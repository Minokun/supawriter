export function normalizeTweetTopicsResponse(payload) {
  const raw = payload?.record ?? payload ?? {}

  if (raw.record_id != null) {
    return raw
  }

  if (raw.id != null) {
    return {
      record_id: raw.id,
      mode: raw.mode ?? 'manual',
      topic_name: raw.topic_name,
      news_source: raw.news_source ?? '',
      news_count: raw.news_count ?? 0,
      topics_data: raw.topics_data ?? { topics: [] },
      model_type: raw.model_type,
      model_name: raw.model_name,
      news_urls: raw.news_urls ?? [],
    }
  }

  return raw
}
