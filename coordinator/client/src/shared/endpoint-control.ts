export const ENDPOINT_CONTROL_URL = "http://127.0.0.1:38019";
const RETRY_DELAY_MS = 75;

export async function requestEndpointControl(
  path,
  options,
  fetcher = fetch,
  wait = (duration) =>
    new Promise((resolve) => {
      window.setTimeout(resolve, duration);
    }),
) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await fetcher(`${ENDPOINT_CONTROL_URL}${path}`, options);
    } catch {
      if (attempt === 1) {
        throw new Error("The local endpoint control bridge is unavailable.");
      }
      await wait(RETRY_DELAY_MS);
    }
  }
}
