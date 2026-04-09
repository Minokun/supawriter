import { redirect } from 'next/navigation';

interface LoginPageProps {
  searchParams?: {
    callbackUrl?: string | string[];
  };
}

export default function LoginPage({ searchParams }: LoginPageProps) {
  const callbackUrl = Array.isArray(searchParams?.callbackUrl)
    ? searchParams?.callbackUrl[0]
    : searchParams?.callbackUrl;

  if (callbackUrl) {
    redirect(`/auth/signin?callbackUrl=${encodeURIComponent(callbackUrl)}`);
  }

  redirect('/auth/signin');
}
