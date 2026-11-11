package main

import (
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
	if os.Getenv("GITHUB_REF_TYPE") != "tag" {
		var candidate struct {
			Source string `json:"source_sha"`
			Tested bool   `json:"tested"`
		}
		data, err := os.ReadFile("dist/candidate.json")
		if err != nil {
			return err
		}
		if err = json.Unmarshal(data, &candidate); err != nil {
			return err
		}
		if candidate.Source != os.Getenv("GITHUB_SHA") || candidate.Tested {
			return fmt.Errorf("candidate does not match this source or is already marked tested")
		}
	}
	c := exec.Command("sha256sum", "-c", "SHA256SUMS")
	c.Dir = "dist"
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
		return fmt.Errorf("expected one candidate archive")
	}
	c = exec.Command("python3", "tests/validate.py", "--chart", files[0])
	c.Stdout, c.Stderr = os.Stdout, os.Stderr
	if e = c.Run(); e != nil {
		return e
	}
	return os.WriteFile("dist/qualification.json", []byte(fmt.Sprintf("{\"tested\":true,\"scope\":\"archive integrity and rendering, not runtime acceptance\",\"source_sha\":%q}\n", os.Getenv("GITHUB_SHA"))), 0644)
}
