"""Provider adapters. Import concrete providers directly to keep the heavy
SDK imports (google-genai, anthropic) lazy — the Gateway loads only the one
it actually uses."""
