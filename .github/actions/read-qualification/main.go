// Read only the tested receipt for the expected promoted archive.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"regexp"
)

func run() error {
	n := os.Getenv("COMPONENT")
	if n != "bastion" && n != "provision" {
		return fmt.Errorf("unknown component")
	}
	var r struct {
		Image, Arch, Revision, Digest string
		Sum                           string `json:"archive_sha256"`
		Tested                        bool
	}
	base := "dist/" + n + "/"
	b, e := os.ReadFile(base + "qualified.json")
	if e != nil {
		return e
	}
	if e = json.Unmarshal(b, &r); e != nil {
		return e
	}
	if !r.Tested || r.Arch != "amd64" || r.Image != n || r.Revision != os.Getenv("GITHUB_SHA") || !regexp.MustCompile(`^sha256:[a-f0-9]{64}$`).MatchString(r.Digest) {
		return fmt.Errorf("incorrect qualification subject")
	}
	f, e := os.Open(base + "image.oci.tar")
	if e != nil {
		return e
	}
	defer f.Close()
	h := sha256.New()
	if _, e = io.Copy(h, f); e != nil {
		return e
	}
	if fmt.Sprintf("%x", h.Sum(nil)) != r.Sum {
		return fmt.Errorf("qualified archive changed")
	}
	out, e := os.OpenFile(os.Getenv("GITHUB_OUTPUT"), os.O_APPEND|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	defer out.Close()
	_, e = fmt.Fprintln(out, "digest="+r.Digest)
	return e
}
func main() {
	if e := run(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
