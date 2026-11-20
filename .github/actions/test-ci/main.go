// Run only the repository's isolated CI operation fixtures.
package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	c := exec.Command("python3", ".github/scripts/test-actions.py")
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	if e := c.Run(); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
