export function getInternalApiUrl(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.API_PROXY_URL ||
    'http://backend:8000'
  );
}
