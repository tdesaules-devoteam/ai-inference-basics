package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
func run() error {
	event, ref := os.Getenv("GITHUB_EVENT_NAME"), os.Getenv("GITHUB_REF")
	if event == "workflow_dispatch" && ref != "refs/heads/main" {
		return fmt.Errorf("manual execution requires main")
	}
	tag := strings.HasPrefix(ref, "refs/tags/")
	if tag && !regexp.MustCompile(`^refs/tags/[0-9]+\.[0-9]+\.[0-9]+$`).MatchString(ref) {
		return fmt.Errorf("invalid stable release tag")
	}
	files, err := exec.Command("git", "-c", "safe.directory=*", "ls-files", "-z").Output()
	if err != nil {
		return err
	}
	shell, yaml, markdown := []string{}, []string{}, []string{}
	containers := []string{}
	for _, f := range strings.Split(string(files), "\x00") {
		if f == "" {
			continue
		}
		if filepath.Base(f) == "Containerfile" {
			containers = append(containers, f)
		}
		switch filepath.Ext(f) {
		case ".sh":
			shell = append(shell, f)
		case ".md":
			markdown = append(markdown, f)
		case ".yaml", ".yml":
			if !strings.Contains(f, "/templates/") {
				yaml = append(yaml, f)
			}
		}
	}
	images := []string{}
	for _, f := range strings.Split(string(files), "\x00") {
		parts := strings.Split(f, "/")
		if len(parts) == 3 && parts[0] == "oci" && parts[2] == "Containerfile" {
			if !regexp.MustCompile(`^[a-z0-9]+(-[a-z0-9]+)*$`).MatchString(parts[1]) {
				return fmt.Errorf("invalid image name %q", parts[1])
			}
			images = append(images, parts[1])
		}
	}
	if len(images) == 0 {
		return fmt.Errorf("no application images discovered")
	}
	all := append([]string{}, images...)
	builds := append([]string{}, images...)
	scans := []string{}
	if tag {
		builds = []string{}
	}
	platform := true
	if event == "push" && !tag {
		body, err := os.ReadFile(os.Getenv("GITHUB_EVENT_PATH"))
		if err != nil {
			return err
		}
		var payload struct {
			Before string `json:"before"`
		}
		if err = json.Unmarshal(body, &payload); err != nil {
			return err
		}
		if payload.Before != "" && strings.Trim(payload.Before, "0") != "" {
			diff, err := exec.Command("git", "-c", "safe.directory=*", "diff", "--no-renames", "--name-only", "-z", payload.Before, "HEAD").Output()
			if err != nil {
				return fmt.Errorf("missing change history: %w", err)
			}
			changed := map[string]bool{}
			retest := map[string]bool{}
			scan := map[string]bool{}
			paths := map[string]bool{}
			platform = false
			for _, f := range strings.Split(string(diff), "\x00") {
				if f == "" {
					continue
				}
				paths[f] = true
				if !strings.HasSuffix(f, ".md") && !strings.HasPrefix(f, "docs/") {
					platform = true
				}
				for _, image := range images {
					if strings.HasPrefix(f, "oci/"+image+"/") || f == ".dockerignore" || f == "oci/prepare.sh" {
						changed[image] = true
					} else if strings.HasPrefix(f, ".github/actions/smoke-"+image+"/") || f == ".github/scripts/smoke-"+image+".py" || f == "infra/infra-definition.sample.json" || strings.HasPrefix(f, ".github/workflows/") {
						retest[image] = true
					} else if strings.HasPrefix(f, ".grype") || strings.HasPrefix(f, ".syft") {
						scan[image] = true
					}
				}
			}
			selected := []string{}
			for _, image := range images {
				if changed[image] || retest[image] || scan[image] {
					selected = append(selected, image)
				}
			}
			builds = []string{}
			for _, n := range selected {
				if changed[n] {
					builds = append(builds, n)
				} else if scan[n] && !retest[n] {
					scans = append(scans, n)
				}
			}
			images = selected
			filter := func(list []string) []string {
				current := []string{}
				for _, f := range list {
					if paths[f] {
						current = append(current, f)
					}
				}
				return current
			}
			shell, yaml, markdown, containers = filter(shell), filter(yaml), filter(markdown), filter(containers)
		}
	}
	output, err := os.OpenFile(os.Getenv("GITHUB_OUTPUT"), os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	defer output.Close()
	releaseRef := ""
	if tag {
		releaseRef = ref
	} else if os.Getenv("GITHUB_WORKFLOW") == "maintenance" || os.Getenv("GITHUB_WORKFLOW") == "release" {
		tags, err := exec.Command("git", "-c", "safe.directory=*", "tag", "--merged", "HEAD", "--sort=-version:refname").Output()
		if err != nil {
			return err
		}
		for _, v := range strings.Fields(string(tags)) {
			if regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(v) {
				releaseRef = "refs/tags/" + v
				break
			}
		}
	}
	digests := map[string]string{}
	if releaseRef != "" {
		annotation, err := exec.Command("git", "-c", "safe.directory=*", "for-each-ref", "--format=%(contents:subject)", releaseRef).Output()
		if err != nil {
			return err
		}

		if err := json.Unmarshal(annotation, &digests); err != nil {
			return fmt.Errorf("tag lacks a qualification annotation: %w", err)
		}
		for _, name := range all {
			if !regexp.MustCompile(`^sha256:[0-9a-f]{64}$`).MatchString(digests[name]) {
				return fmt.Errorf("tag lacks %s digest", name)
			}
		}
	} else {
		var env struct {
			Images map[string]string `json:"images"`
		}
		data, e := os.ReadFile("infra/infra-definition.sample.json")
		if e != nil {
			return e
		}
		if e = json.Unmarshal(data, &env); e != nil {
			return e
		}
		for _, n := range all {
			prefix := "ghcr.io/" + os.Getenv("GITHUB_REPOSITORY") + "/" + n + "@"
			ref := env.Images[n]
			digest, ok := strings.CutPrefix(ref, prefix)
			if !ok || !regexp.MustCompile(`^sha256:[a-f0-9]{64}$`).MatchString(digest) {
				return fmt.Errorf("missing deployed digest for %s", n)
			}
			digests[n] = digest
		}
	}
	if releaseRef != "" && event == "workflow_dispatch" && os.Getenv("GITHUB_WORKFLOW") == "release" {
		builds = []string{}
		for _, n := range all {
			b, e := exec.Command("git", "-c", "safe.directory=*", "diff", "--name-only", releaseRef, "HEAD", "--", "oci/"+n, "oci/prepare.sh", ".dockerignore").Output()
			if e != nil {
				return e
			}
			if len(b) > 0 {
				builds = append(builds, n)
			}
		}
	}
	{
		compact, _ := json.Marshal(digests)
		fmt.Fprintf(output, "digests=%s\n", compact)
	}
	if os.Getenv("LAB_HELPERS") == "true" {
		if event != "workflow_dispatch" || ref != "refs/heads/main" || os.Getenv("GITHUB_WORKFLOW") != "release" {
			return fmt.Errorf("helper publication requires release dispatch on main")
		}
		images = []string{}
		for _, f := range strings.Split(string(files), "\x00") {
			parts := strings.Split(f, "/")
			if len(parts) == 4 && parts[0] == ".github" && parts[1] == "actions" && parts[3] == "Containerfile" {
				images = append(images, parts[2])
			}
		}
		if len(images) == 0 {
			return fmt.Errorf("no helper recipes")
		}
		builds = images
	}
	reused := map[string]string{}
	for _, n := range images {
		build := false
		for _, x := range builds {
			if n == x {
				build = true
				break
			}
		}
		if !build {
			reused[n] = digests[n]
		}
	}
	reuseJSON, _ := json.Marshal(reused)
	fmt.Fprintf(output, "reused=%s\n", reuseJSON)
	b, _ := json.Marshal(builds)
	sc, _ := json.Marshal(scans)
	fmt.Fprintf(output, "build_images=%s\nscan_only=%s\n", b, sc)
	matrix, err := json.Marshal(images)
	if err != nil {
		return err
	}
	fmt.Fprintf(output, "images=%s\nhas_build=%t\nhas_tests=%t\n", matrix, len(builds) > 0, len(images) > 0)
	fmt.Fprintf(output, "platform=%t\n", platform)
	for k, v := range map[string][]string{"shell_files": shell, "yaml_files": yaml, "markdown_files": markdown, "container_files": containers} {
		b, _ := json.Marshal(v)
		fmt.Fprintf(output, "%s=%s\n", k, b)
	}
	return nil
}
