package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
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

type fakeChatClient struct {
	response string
	messages []chatMessage
	calls    int
}

func (f *fakeChatClient) Send(_ context.Context, messages []chatMessage) (string, error) {
	f.calls++
	f.messages = append([]chatMessage(nil), messages...)
	return f.response, nil
}

type doerFunc func(req *http.Request) (*http.Response, error)

func (f doerFunc) Do(req *http.Request) (*http.Response, error) {
	return f(req)
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
	if !strings.Contains(output, "dndx chat") {
		t.Fatalf("stdout missing banner: %s", output)
	}
	if !strings.Contains(output, "Provider: lmstudio") {
		t.Fatalf("stdout missing status: %s", output)
	}
}

func TestInteractivePromptBlinksUnderscore(t *testing.T) {
	if !strings.Contains(interactivePrompt, ansiBlink+"_") {
		t.Fatalf("prompt should blink underscore: %q", interactivePrompt)
	}
	if !strings.Contains(interactivePrompt, "_"+ansiReset) {
		t.Fatalf("prompt should reset after underscore: %q", interactivePrompt)
	}
}

func TestInteractiveModeSendsPlainTextToChat(t *testing.T) {
	question := "provide a brief random encounter table for 3 first-level characters. They are in the woods."
	app, stdout, stderr, configPath := newTestApp(t, question+"\n/quit\n")
	if err := saveConfig(configPath, Config{
		Provider:  providerLMStudio,
		Endpoint:  defaultLMStudioEndpoint,
		ChatModel: "glm-5.0",
	}); err != nil {
		t.Fatal(err)
	}

	fake := &fakeChatClient{response: "1. Three nervous scouts cross the trail."}
	var factoryConfig Config
	app.chatFactory = func(config Config) (chatClient, error) {
		factoryConfig = config
		return fake, nil
	}

	code := app.Run(nil)

	if code != 0 {
		t.Fatalf("expected success, got %d: %s", code, stderr.String())
	}
	if fake.calls != 1 {
		t.Fatalf("chat calls = %d", fake.calls)
	}
	if factoryConfig.ChatModel != "glm-5.0" {
		t.Fatalf("factory config = %+v", factoryConfig)
	}
	if len(fake.messages) != 2 {
		t.Fatalf("messages = %+v", fake.messages)
	}
	if fake.messages[0].Role != "system" {
		t.Fatalf("first message = %+v", fake.messages[0])
	}
	if fake.messages[1].Role != "user" || fake.messages[1].Content != question {
		t.Fatalf("user message = %+v", fake.messages[1])
	}
	output := stdout.String()
	if !strings.Contains(output, interactivePrompt) {
		t.Fatalf("stdout missing prompt: %s", output)
	}
	if !strings.Contains(output, "Thinking...") {
		t.Fatalf("stdout missing thinking line: %s", output)
	}
	if !strings.Contains(output, "Three nervous scouts") {
		t.Fatalf("stdout missing response: %s", output)
	}
}

func TestDirectChatCommandSendsQuestion(t *testing.T) {
	app, stdout, stderr, configPath := newTestApp(t, "")
	if err := saveConfig(configPath, Config{
		Provider:  providerLMStudio,
		Endpoint:  defaultLMStudioEndpoint,
		ChatModel: "glm-5.0",
	}); err != nil {
		t.Fatal(err)
	}

	fake := &fakeChatClient{response: "Roll 1d4 wolves."}
	app.chatFactory = func(_ Config) (chatClient, error) {
		return fake, nil
	}

	code := app.Run([]string{"chat", "provide", "a", "brief", "encounter"})

	if code != 0 {
		t.Fatalf("expected success, got %d: %s", code, stderr.String())
	}
	if fake.calls != 1 {
		t.Fatalf("chat calls = %d", fake.calls)
	}
	if got := fake.messages[len(fake.messages)-1].Content; got != "provide a brief encounter" {
		t.Fatalf("question = %q", got)
	}
	if !strings.Contains(stdout.String(), "Roll 1d4 wolves") {
		t.Fatalf("stdout = %s", stdout.String())
	}
}

func TestChatRequiresConfiguredEndpoint(t *testing.T) {
	app, _, stderr, _ := newTestApp(t, "")

	code := app.Run([]string{"chat", "hello"})

	if code == 0 {
		t.Fatal("expected failure")
	}
	if !strings.Contains(stderr.String(), "no model endpoint configured") {
		t.Fatalf("stderr = %s", stderr.String())
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

func TestOpenAIChatClientSendsChatCompletionRequest(t *testing.T) {
	client := openAIChatClient{
		endpoint: "http://lmstudio.test/v1/chat/completions",
		model:    "glm-5.0",
		doer: doerFunc(func(req *http.Request) (*http.Response, error) {
			if req.Method != http.MethodPost {
				t.Fatalf("method = %s", req.Method)
			}
			if req.URL.Path != "/v1/chat/completions" {
				t.Fatalf("path = %s", req.URL.Path)
			}

			var payload struct {
				Model    string        `json:"model"`
				Messages []chatMessage `json:"messages"`
				Stream   bool          `json:"stream"`
			}
			if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
				t.Fatal(err)
			}
			if payload.Model != "glm-5.0" {
				t.Fatalf("model = %q", payload.Model)
			}
			if len(payload.Messages) != 1 || payload.Messages[0].Content != "encounter" {
				t.Fatalf("messages = %+v", payload.Messages)
			}
			if payload.Stream {
				t.Fatal("stream should be false")
			}

			return &http.Response{
				StatusCode: http.StatusOK,
				Header:     make(http.Header),
				Body:       io.NopCloser(strings.NewReader(`{"choices":[{"message":{"role":"assistant","content":"Roll 1d4 wolves."}}]}`)),
			}, nil
		}),
	}

	answer, err := client.Send(context.Background(), []chatMessage{{Role: "user", Content: "encounter"}})

	if err != nil {
		t.Fatal(err)
	}
	if answer != "Roll 1d4 wolves." {
		t.Fatalf("answer = %q", answer)
	}
}

func TestOllamaChatClientSendsNativeChatRequest(t *testing.T) {
	client := ollamaChatClient{
		endpoint: "http://ollama.test/api/chat",
		model:    "llama3.2",
		doer: doerFunc(func(req *http.Request) (*http.Response, error) {
			if req.Method != http.MethodPost {
				t.Fatalf("method = %s", req.Method)
			}
			if req.URL.Path != "/api/chat" {
				t.Fatalf("path = %s", req.URL.Path)
			}

			var payload struct {
				Model    string        `json:"model"`
				Messages []chatMessage `json:"messages"`
				Stream   bool          `json:"stream"`
			}
			if err := json.NewDecoder(req.Body).Decode(&payload); err != nil {
				t.Fatal(err)
			}
			if payload.Model != "llama3.2" {
				t.Fatalf("model = %q", payload.Model)
			}
			if len(payload.Messages) != 1 || payload.Messages[0].Content != "encounter" {
				t.Fatalf("messages = %+v", payload.Messages)
			}
			if payload.Stream {
				t.Fatal("stream should be false")
			}

			return &http.Response{
				StatusCode: http.StatusOK,
				Header:     make(http.Header),
				Body:       io.NopCloser(strings.NewReader(`{"message":{"role":"assistant","content":"Use two scouts and a lost map."}}`)),
			}, nil
		}),
	}

	answer, err := client.Send(context.Background(), []chatMessage{{Role: "user", Content: "encounter"}})

	if err != nil {
		t.Fatal(err)
	}
	if answer != "Use two scouts and a lost map." {
		t.Fatalf("answer = %q", answer)
	}
}
