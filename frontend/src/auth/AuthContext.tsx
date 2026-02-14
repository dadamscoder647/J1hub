import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';
import { authService } from '../api/services';
import { User } from '../types/api';
import { storage } from '../utils/storage';

interface AuthContextShape {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextShape | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(storage.getUser());
  const [token, setToken] = useState<string | null>(storage.getAccessToken());

  const value = useMemo(
    () => ({
      user,
      token,
      login: async (email: string, password: string) => {
        const result = await authService.login({ email, password });
        storage.setAccessToken(result.access_token);
        storage.setUser(result.user);
        setToken(result.access_token);
        setUser(result.user);
      },
      logout: () => {
        storage.clearAll();
        setUser(null);
        setToken(null);
      },
    }),
    [user, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
