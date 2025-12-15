"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import apiClient from "@/lib/api/client";

const PUBLIC_PATHS = ["/login", "/forgot-password", "/reset-password"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = apiClient.getToken();
    const isPublicPath = PUBLIC_PATHS.some((path) => pathname.startsWith(path));

    if (!token && !isPublicPath) {
      router.replace("/login");
    } else if (token && pathname === "/login") {
      router.replace("/");
    } else {
      setIsAuthenticated(!!token || isPublicPath);
    }
    setIsLoading(false);
  }, [pathname, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated && !PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
    return null;
  }

  return <>{children}</>;
}
