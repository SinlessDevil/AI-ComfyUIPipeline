# Optional OpenAI image integration

## ComfyUI Partner Nodes

The application includes OpenAI Partner Node implementations. Their model choices and input schemas depend on the installed ComfyUI version. Consult the selected node and the [official ComfyUI guide](https://docs.comfy.org/tutorials/api-nodes/openai/gpt-image-1).

Partner Nodes use Comfy authentication/credits. Setting `OPENAI_API_KEY` in a local `.env` does not configure their Comfy credentials. A paid workflow can connect an optional reference image to an OpenAI image node and then `Save Image`, but enable spending only after explicit authorization. The prepared local art workflows do not require this service.

## Direct OpenAI API

A separate adapter using the user's own OpenAI project would be a different integration. A possible design is a custom node under `ComfyUI/custom_nodes/` that reads credentials server-side, makes a request only when its graph runs, and returns `IMAGE` to the existing resize/alpha/save stages. Do not modify core ComfyUI to add outbound requests.

No direct API adapter is installed by this local setup. The launcher does not automatically load `.env`; `.env.example` is only a placeholder. Any future adapter must explicitly read its configuration. Keep credentials out of widgets, workflow metadata, source, README files, and logs. Do not print credentials during diagnostics.

Before implementing an adapter, check the current [image generation guide](https://developers.openai.com/api/docs/guides/image-generation) and [API reference](https://developers.openai.com/api/reference/resources/images/methods/generate) for supported models, generation/edit inputs, mask requirements, and transparency options. This document does not guarantee availability of a particular hosted model or authorize paid requests.
