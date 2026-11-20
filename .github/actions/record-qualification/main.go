// Record the verified identity only after the candidate has executed successfully.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
)

type receipt struct {
	Image    string `json:"image"`
	Arch     string `json:"arch"`
	Revision string `json:"revision"`
	Version  string `json:"version"`
	Sum      string `json:"archive_sha256"`
	Digest   string `json:"digest"`
	Tested   bool   `json:"tested"`
}

func run() error {
	var r receipt
	b, err := os.ReadFile("dist/build.json")
	if err != nil {
		return err
	}
	if err = json.Unmarshal(b, &r); err != nil {
		return err
	}
	digest := os.Getenv("CANDIDATE_DIGEST")
	if !regexp.MustCompile(`^sha256:[0-9a-f]{64}$`).MatchString(digest) || r.Tested || r.Revision != os.Getenv("GITHUB_SHA") || r.Image != os.Getenv("COMPONENT") || r.Arch != "amd64" || r.Version != r.Revision {
		return fmt.Errorf("qualification source mismatch")
	}
	f, err := os.Open("dist/image.oci.tar")
	if err != nil {
		return err
	}
	defer f.Close()
	h := sha256.New()
	if _, err = io.Copy(h, f); err != nil {
		return err
	}
	if fmt.Sprintf("%x", h.Sum(nil)) != r.Sum {
		return fmt.Errorf("archive changed after runtime test")
	}
	r.Digest = digest
	r.Tested = true
	b, err = json.Marshal(r)
	if err != nil {
		return err
	}
	return os.WriteFile("dist/qualified.json", b, 0644)
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
