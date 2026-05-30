package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func newTestApp(t *testing.T, stdin string) (*App, *bytes.Buffer, *bytes.Buffer, string) {
	t.Helper()
	configPath := filepath.Join(t.TempDir(), "config.json")
	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	app := NewApp(strings.NewReader(stdin), stdout, stderr, configPath)
	return app, stdout, stderr, configPath
}

func TestConnectLMStudioNormalizesBareEndpoint(t *testing.T) {
	app, stdout, stderr, configPath := newTestApp(t, "")

	code := app.Run([]string{"/connect", "lmstudio", "--url", "http://127.0.0.1:1234"})

	if code != 0 {
		t.Fatalf("expected success, got %d: %s", code, stderr.String())
	}
	config, err := loadConfig(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if config.Provider != providerLMStudio {
		t.Fatalf("provider = %q", config.Provider)
	}
	if config.Endpoint != "http://127.0.0.1:1234/v1" {
		t.Fatalf("endpoint = %q", config.Endpoint)
	}
	if !strings.Contains(stdout.String(), "Connected to lmstudio") {
		t.Fatalf("stdout did not mention connection: %s", stdout.String())
	}
}

func TestConnectOllamaUsesDefaultEndpoint(t *testing.T) {
	app, _, stderr, configPath := newTestApp(t, "")

	code := app.Run([]string{"/connect", "ollama"})

	if code != 0 {
		t.Fatalf("expected success, got %d: %s", code, stderr.String())
	}
	config, err := loadConfig(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if config.Endpoint != defaultOllamaEndpoint {
		t.Fatalf("endpoint = %q", config.Endpoint)
	}
}

func TestModelsConfigureChatAndEmbeddingModels(t *testing.T) {
	app, stdout, stderr, configPath := newTestApp(t, "")

	if code := app.Run([]string{"connect", "lmstudio"}); code != 0 {
		t.Fatalf("connect failed: %s", stderr.String())
	}
	stdout.Reset()
	if code := app.Run([]string{"models", "--chat", "glm-5.0", "--embedding=text-embedding-nomic-embed-text-v1.5"}); code != 0 {
		t.Fatalf("models failed: %s", stderr.String())
	}

	config, err := loadConfig(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if config.ChatModel != "glm-5.0" {
		t.Fatalf("chat model = %q", config.ChatModel)
	}
	if config.EmbeddingModel != "text-embedding-nomic-embed-text-v1.5" {
		t.Fatalf("embedding model = %q", config.EmbeddingModel)
	}
	if !strings.Contains(stdout.String(), "Configured models") {
		t.Fatalf("stdout = %s", stdout.String())
	}
}

func TestModelsPrintsExistingConfig(t *testing.T) {
	app, stdout, stderr, _ := newTestApp(t, "")

	if code := app.Run([]string{"connect", "lmstudio"}); code != 0 {
		t.Fatalf("connect failed: %s", stderr.String())
	}
	if code := app.Run([]string{"models", "--chat", "chatty", "--embedding", "embedder"}); code != 0 {
		t.Fatalf("models failed: %s", stderr.String())
	}
	stdout.Reset()

	if code := app.Run([]string{"models"}); code != 0 {
		t.Fatalf("models print failed: %s", stderr.String())
	}

	output := stdout.String()
	if !strings.Contains(output, "Chat model: chatty") {
		t.Fatalf("stdout missing chat model: %s", output)
	}
	if !strings.Contains(output, "Embedding model: embedder") {
		t.Fatalf("stdout missing embedding model: %s", output)
	}
}

func TestInteractiveModeProcessesCommands(t *testing.T) {
	app, stdout, stderr, configPath := newTestApp(
		t,
		"/connect lmstudio --url http://localhost:1234\nmodels --chat chat --embedding embed\nstatus\n/quit\n",
	)

	code := app.Run(nil)

	if code != 0 {
		t.Fatalf("expected success, got %d: %s", code, stderr.String())
	}
	config, err := loadConfig(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if config.ChatModel != "chat" || config.EmbeddingModel != "embed" {
		t.Fatalf("config = %+v", config)
	}
	output := stdout.String()
	if !strings.Contains(output, "dndx CLI") {
		t.Fatalf("stdout missing banner: %s", output)
	}
	if !strings.Contains(output, "Provider: lmstudio") {
		t.Fatalf("stdout missing status: %s", output)
	}
}

func TestUnknownProviderReturnsUsageError(t *testing.T) {
	app, _, stderr, _ := newTestApp(t, "")

	code := app.Run([]string{"/connect", "kobold"})

	if code == 0 {
		t.Fatal("expected failure")
	}
	if !strings.Contains(stderr.String(), "provider must be lmstudio or ollama") {
		t.Fatalf("stderr = %s", stderr.String())
	}
}

func TestConfigPathFromEnvironment(t *testing.T) {
	t.Setenv("DNDX_CONFIG", filepath.Join("tmp", "dndx.json"))

	if got := configPathFromEnv(); got != filepath.Join("tmp", "dndx.json") {
		t.Fatalf("config path = %q", got)
	}
}

func TestLoadConfigMissingFileReturnsEmptyConfig(t *testing.T) {
	config, err := loadConfig(filepath.Join(t.TempDir(), "missing.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !isEmptyConfig(config) {
		t.Fatalf("config should be empty: %+v", config)
	}
}

func TestSaveConfigCreatesPrivateConfigFile(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "nested", "config.json")
	config := Config{Provider: providerLMStudio, Endpoint: defaultLMStudioEndpoint}

	if err := saveConfig(configPath, config); err != nil {
		t.Fatal(err)
	}

	info, err := os.Stat(configPath)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("mode = %v", info.Mode().Perm())
	}
}
