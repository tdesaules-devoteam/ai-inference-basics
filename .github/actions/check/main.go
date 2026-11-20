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
	images := []string{"bastion", "provision"}
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
					if strings.HasPrefix(f, "oci/"+image+"/") || f == ".dockerignore" || f == "oci/prepare.sh" || strings.HasPrefix(f, ".github/") {
						changed[image] = true
					}
				}
			}
			selected := []string{}
			for _, image := range images {
				if changed[image] {
					selected = append(selected, image)
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
	} else if os.Getenv("GITHUB_WORKFLOW") == "maintenance" {
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
	if releaseRef != "" {
		annotation, err := exec.Command("git", "-c", "safe.directory=*", "for-each-ref", "--format=%(contents:subject)", releaseRef).Output()
		if err != nil {
			return err
		}
		var digests map[string]string
		if err := json.Unmarshal(annotation, &digests); err != nil {
			return fmt.Errorf("tag lacks a qualification annotation: %w", err)
		}
		for _, name := range images {
			if !regexp.MustCompile(`^sha256:[0-9a-f]{64}$`).MatchString(digests[name]) {
				return fmt.Errorf("tag lacks %s digest", name)
			}
		}
		compact, _ := json.Marshal(digests)
		fmt.Fprintf(output, "digests=%s\n", compact)
	}
	matrix, err := json.Marshal(images)
	if err != nil {
		return err
	}
	fmt.Fprintf(output, "images=%s\nhas_build=%t\nhas_tests=%t\n", matrix, len(images) > 0 && !tag, len(images) > 0)
	fmt.Fprintf(output, "platform=%t\n", platform)
	for k, v := range map[string][]string{"shell_files": shell, "yaml_files": yaml, "markdown_files": markdown, "container_files": containers} {
		b, _ := json.Marshal(v)
		fmt.Fprintf(output, "%s=%s\n", k, b)
	}
	return nil
}
