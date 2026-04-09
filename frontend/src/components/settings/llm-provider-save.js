export function mergeProviderModelEdits(providers, editedModelsByProviderId = {}) {
  return providers.map((provider) => {
    const editedModels = editedModelsByProviderId[provider.id]
    if (!editedModels) {
      return provider
    }

    return {
      ...provider,
      models: editedModels,
    }
  })
}

export function buildLlmProvidersSavePayload(providers, editedModelsByProviderId = {}) {
  return mergeProviderModelEdits(providers, editedModelsByProviderId).map((provider) => ({
    ...provider,
    api_key: provider.api_key === '••••••••' ? undefined : provider.api_key,
  }))
}
