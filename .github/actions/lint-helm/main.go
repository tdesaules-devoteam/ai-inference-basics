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
	command("", "python3", "tests/validate.py")
	command("", "python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
}
