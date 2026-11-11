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
	for _, p := range []string{"local-cpu", "scaleway-cpu-pilot", "scaleway-h100"} {
		command("", "helm", "lint", "--strict", chart, "-f", "profiles/"+p+".yaml")
	}
	command("", "python3", ".github/scripts/validate-chart.py")
}
