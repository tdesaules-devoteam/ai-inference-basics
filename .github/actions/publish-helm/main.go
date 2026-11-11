package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
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
	var qualification struct {
		Tested bool   `json:"tested"`
		Source string `json:"source_sha"`
	}
	b, e := os.ReadFile("dist/qualification.json")
	if e != nil {
		return e
	}
	if e = json.Unmarshal(b, &qualification); e != nil {
		return e
	}
	if !qualification.Tested || qualification.Source != os.Getenv("GITHUB_SHA") {
		return fmt.Errorf("missing qualification for this source")
	}
	c := exec.Command("sha256sum", "-c", "SHA256SUMS")
	c.Dir = "dist"
	if e = c.Run(); e != nil {
		return e
	}
	files, e := filepath.Glob("dist/*.tgz")
	if e != nil {
		return e
	}
	if len(files) != 1 {
		return fmt.Errorf("expected one qualified chart")
	}
	repo := strings.ToLower(os.Getenv("GITHUB_REPOSITORY"))
	if repo != "tdesaules-devoteam/ai-inference-basics" {
		return fmt.Errorf("unexpected publication repository")
	}
	c = exec.Command("helm", "registry", "login", "ghcr.io", "--username", os.Getenv("GITHUB_ACTOR"), "--password-stdin")
	c.Stdin = strings.NewReader(os.Getenv("REGISTRY_TOKEN"))
	c.Stderr = os.Stderr
	if e = c.Run(); e != nil {
		return e
	}
	defer exec.Command("helm", "registry", "logout", "ghcr.io").Run()
	target := "oci://ghcr.io/" + repo + "/charts"
	// Refuse replacement of an existing version, even if registry tags are mutable.
	version := strings.TrimSuffix(strings.TrimPrefix(filepath.Base(files[0]), "ai-inference-basics-"), ".tgz")
	existing := exec.Command("helm", "show", "chart", target+"/ai-inference-basics", "--version", version)
	if existing.Run() == nil {
		return fmt.Errorf("chart version already exists; publish a new version instead")
	}
	out, e := exec.Command("helm", "push", files[0], target).CombinedOutput()
	if e != nil {
		return fmt.Errorf("publication failed: %s", out)
	}
	digest := regexp.MustCompile(`sha256:[a-f0-9]{64}`).FindString(string(out))
	if digest == "" {
		return fmt.Errorf("registry digest missing")
	}
	dir, e := os.MkdirTemp("", "ai-inference-basics-pull-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(dir)
	c = exec.Command("helm", "pull", target+"/ai-inference-basics@"+digest, "--destination", dir)
	c.Stderr = os.Stderr
	if e = c.Run(); e != nil {
		return e
	}
	pulled, e := os.ReadFile(filepath.Join(dir, filepath.Base(files[0])))
	if e != nil {
		return e
	}
	original, e := os.ReadFile(files[0])
	if e != nil {
		return e
	}
	if !bytes.Equal(original, pulled) {
		return fmt.Errorf("published chart bytes differ from qualified archive")
	}
	sum := sha256.Sum256(original)
	receipt, _ := json.MarshalIndent(map[string]string{"reference": target + "/ai-inference-basics@" + digest, "version": version, "sha256": hex.EncodeToString(sum[:]), "source_sha": os.Getenv("GITHUB_SHA")}, "", "  ")
	return os.WriteFile("dist/publication.json", append(receipt, '\n'), 0644)
}
