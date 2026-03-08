declare global {
  interface Window {
    ashwen?: {
      backend?: {
        httpUrl?: string;
        wsUrl?: string;
      };
      app?: {
        version?: string;
        platform?: string;
        isPackaged?: boolean;
      };
    };
  }
}

export {};
