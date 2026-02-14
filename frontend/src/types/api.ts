export type Role = 'worker' | 'employer' | 'admin';

export interface User {
  id: number;
  email: string;
  role: Role;
}

export interface AuthResponse {
  access_token: string;
  user: User;
}

export interface Listing {
  id: number;
  category: string;
  title: string;
  description: string;
  company_name?: string;
  contact_method?: string | null;
  contact_value?: string | null;
  location_city?: string;
  is_public: boolean;
  is_active: boolean;
}

export interface VerificationStatusResponse {
  verification_status: string;
  latest_document: { id: number; status: string; filename: string } | null;
}

export interface SubscriptionStatus {
  hasActiveSubscription: boolean;
  listingCredits: number;
}
