export interface User {
  id: string;
  username: string;
  email: string;
  createdAt: string;
}

export const AUTH_ENABLED = false;

interface AuthResult {
  success: boolean;
  error?: string;
}

const LOCAL_USER: User = {
  id: "local",
  username: "Local User",
  email: "",
  createdAt: "1970-01-01T00:00:00.000Z",
};

export function useAuth() {
  return {
    user: LOCAL_USER,
    loading: false,
    signUp: (_username: string, _email: string, _password: string): AuthResult => ({ success: true }),
    signIn: (_identifier: string, _password: string): AuthResult => ({ success: true }),
    signOut: (): void => undefined,
  };
}
