import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import AnimationsTestClient from './AnimationsTestClient';

const AUTH_COOKIE_NAMES = [
  'next-auth.session-token',
  '__Secure-next-auth.session-token',
  'backend-token',
];

export default function AnimationsTestPage() {
  if (process.env.NODE_ENV !== 'development') {
    redirect('/writer');
  }

  const cookieStore = cookies();
  const isAuthenticated = AUTH_COOKIE_NAMES.some((name) => cookieStore.get(name)?.value);

  if (!isAuthenticated) {
    redirect('/auth/signin?callbackUrl=%2Fanimations-test');
  }

  return <AnimationsTestClient />;
}
