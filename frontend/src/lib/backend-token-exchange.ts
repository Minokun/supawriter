export interface BackendTokenExchangeUser {
  email?: string | null;
  name?: string | null;
  id?: string | null;
  image?: string | null;
}

function toNumericUserId(value: string | null | undefined): number | null {
  if (!value || !/^\d+$/.test(value)) {
    return null;
  }

  return Number(value);
}

export function buildBackendTokenExchangePayload(user: BackendTokenExchangeUser) {
  const userId = toNumericUserId(user.id);

  return {
    email: user.email ?? '',
    name: user.name ?? undefined,
    ...(userId !== null ? { user_id: userId } : user.id ? { google_id: user.id } : {}),
    picture: user.image ?? null,
  };
}
