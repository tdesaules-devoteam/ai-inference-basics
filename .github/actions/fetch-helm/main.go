package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"
)

func main() {
	if e := run(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
func run() error {
	var r struct {
		Reference string `json:"reference"`
		Version   string `json:"version"`
		SHA256    string `json:"sha256"`
	}
	b, e := os.ReadFile("charts/release.json")
	if e != nil {
		return fmt.Errorf("record the verified OCI receipt in charts/release.json before tagging: %w", e)
	}
	if e = json.Unmarshal(b, &r); e != nil {
		return e
	}
	if r.Version != strings.TrimPrefix(os.Getenv("GITHUB_REF"), "refs/tags/") {
		return fmt.Errorf("tag and chart version differ")
	}
	if !regexp.MustCompile(`^oci://ghcr.io/tdesaules-devoteam/ai-inference-basics/charts/ai-inference-basics@sha256:[a-f0-9]{64}$`).MatchString(r.Reference) {
		return fmt.Errorf("invalid immutable chart reference")
	}
	if !regexp.MustCompile(`^[a-f0-9]{64}$`).MatchString(r.SHA256) {
		return fmt.Errorf("missing archive checksum")
	}
	if e = os.MkdirAll("dist", 0755); e != nil {
		return e
	}
	c := exec.Command("helm", "pull", r.Reference, "--destination", "dist")
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	if e = c.Run(); e != nil {
		return e
	}
	return os.WriteFile("dist/SHA256SUMS", []byte(r.SHA256+"  ai-inference-basics-"+r.Version+".tgz\n"), 0644)
}
