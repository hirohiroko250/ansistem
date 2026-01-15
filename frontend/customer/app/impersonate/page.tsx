"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function ImpersonateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("認証中...");

  useEffect(() => {
    const token = searchParams.get("token");

    if (!token) {
      setStatus("error");
      setMessage("トークンが見つかりません");
      return;
    }

    try {
      // トークンをlocalStorageに保存
      localStorage.setItem("access_token", token);

      setStatus("success");
      setMessage("ログイン成功！リダイレクト中...");

      // ホームページにリダイレクト
      setTimeout(() => {
        router.replace("/");
      }, 500);
    } catch (error) {
      console.error("Impersonate error:", error);
      setStatus("error");
      setMessage("ログインに失敗しました");
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {status === "loading" && (
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        )}
        {status === "success" && (
          <div className="text-green-600 text-4xl mb-4">✓</div>
        )}
        {status === "error" && (
          <div className="text-red-600 text-4xl mb-4">✕</div>
        )}
        <p className={`text-lg ${status === "error" ? "text-red-600" : "text-gray-700"}`}>
          {message}
        </p>
      </div>
    </div>
  );
}

export default function ImpersonatePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-lg text-gray-700">認証中...</p>
        </div>
      </div>
    }>
      <ImpersonateContent />
    </Suspense>
  );
}
