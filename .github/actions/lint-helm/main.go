package main

import (
	"fmt"
	"os"
	"os/exec"
)

func command(dir, name string, args ...string) {
	c := exec.Command(name, args...)
	c.Dir = dir
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	if e := c.Run(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
func main() {
	const chart = "charts/ai-inference-basics"
	command(chart, "sha256sum", "-c", "dependencies.sha256")
	command("", "python3", "tests/validate.py")
}
