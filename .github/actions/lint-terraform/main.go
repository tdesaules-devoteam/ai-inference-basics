package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	for _, args := range [][]string{
		{"-chdir=infra/terraform", "fmt", "-check", "-recursive"},
		{"-chdir=infra/terraform", "init", "-backend=false", "-input=false", "-lockfile=readonly"},
		{"-chdir=infra/terraform", "validate"},
	} {
		c := exec.Command("terraform", args...)
		c.Env = append(os.Environ(), "TF_IN_AUTOMATION=1", "TF_DATA_DIR=/tmp/ai-inference-basics-terraform")
		c.Stdout, c.Stderr = os.Stdout, os.Stderr
		if e := c.Run(); e != nil {
			fmt.Fprintln(os.Stderr, e)
			os.Exit(1)
		}
	}
}
