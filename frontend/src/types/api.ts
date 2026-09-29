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

export interface PendingVerificationDocument {
  id: number;
  user_id: number;
  filename: string;
  created_at: string | null;
}

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface ApplicationSummary {
  id: number;
  user_id: number;
  listing_id: number;
  message: string;
  status: 'new' | 'reviewing' | 'accepted' | 'rejected';
  created_at: string | null;
}

export interface SubscriptionStatus {
  listing_credits: number;
  has_active_subscription: boolean;
  active_until: string | null;
}
