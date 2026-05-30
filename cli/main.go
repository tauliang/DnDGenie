package main

import "os"

func main() {
	os.Exit(NewApp(os.Stdin, os.Stdout, os.Stderr, configPathFromEnv()).Run(os.Args[1:]))
}
