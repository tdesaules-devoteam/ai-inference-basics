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
	if tag {
		body, err := os.ReadFile("reports/training/G6/acceptance.json")
		if err != nil {
			return fmt.Errorf("stable releases require completed training acceptance: %w", err)
		}
		var gate struct {
			Passed bool `json:"passed"`
		}
		if err = json.Unmarshal(body, &gate); err != nil || !gate.Passed {
			return fmt.Errorf("training acceptance has not passed")
		}
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
	selected := true
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
			diff, err := exec.Command("git", "-c", "safe.directory=*", "diff", "--name-only", "-z", payload.Before, "HEAD").Output()
			if err != nil {
				return fmt.Errorf("missing change history: %w", err)
			}
			selected = false
			for _, f := range strings.Split(string(diff), "\x00") {
				if f == "" {
					continue
				}
				if !strings.HasPrefix(f, "docs/") && !strings.HasSuffix(f, ".md") {
					selected = true
				}
			}
		}
	}
	output, err := os.OpenFile(os.Getenv("GITHUB_OUTPUT"), os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	defer output.Close()
	fmt.Fprintf(output, "has_build=%t\nhas_tests=%t\n", selected && !tag, selected)
	for k, v := range map[string][]string{"shell_files": shell, "yaml_files": yaml, "markdown_files": markdown, "container_files": containers} {
		b, _ := json.Marshal(v)
		fmt.Fprintf(output, "%s=%s\n", k, b)
	}
	return nil
}
