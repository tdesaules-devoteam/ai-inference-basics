package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	if e := run(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
func run() error {
	if e := os.MkdirAll("dist", 0755); e != nil {
		return e
	}
	c := exec.Command("helm", "package", "charts/ai-inference-basics", "--destination", "dist")
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	if e := c.Run(); e != nil {
		return e
	}
	files, e := filepath.Glob("dist/*.tgz")
	if e != nil {
		return e
	}
	if len(files) != 1 {
		return fmt.Errorf("expected exactly one candidate archive")
	}
	b, e := os.ReadFile(files[0])
	if e != nil {
		return e
	}
	h := sha256.Sum256(b)
	if e = os.WriteFile("dist/SHA256SUMS", []byte(hex.EncodeToString(h[:])+"  "+filepath.Base(files[0])+"\n"), 0644); e != nil {
		return e
	}
	receipt, _ := json.Marshal(map[string]any{"tested": false, "source_sha": os.Getenv("GITHUB_SHA"), "archive": filepath.Base(files[0]), "sha256": hex.EncodeToString(h[:])})
	return os.WriteFile("dist/candidate.json", append(receipt, '\n'), 0644)
}
