export type Category = 'INBOX' | 'ACTIVE_HEALTH' | 'ACTIVE_FAMILY' | 'ACTIVE_BUSINESS' | 'PARKING' | 'ARCHIVE';
export type Source = 'voice' | 'text';
export type UserRole = 'user' | 'admin';
export type BucketTab = 'capture' | 'review' | 'buckets' | 'settings';

export interface Thought {
  id: string;
  text: string;
  createdAt: string;
  category: Category;
  note?: string;
  done?: boolean;
  source: Source;
}

export interface AppUser {
  id: string;
  name: string;
  role: UserRole;
}

export interface AppState {
  thoughts: Thought[];
  users: AppUser[];
  settings: {
    reviewTime: string;
    claudeApiKey: string;
    dailyReminderEnabled: boolean;
  };
}
