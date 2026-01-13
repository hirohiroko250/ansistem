# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - img "OZA" [ref=e5]
    - generic [ref=e7]:
      - heading "ログイン" [level=2] [ref=e8]
      - generic [ref=e9]:
        - generic [ref=e10]:
          - generic [ref=e11]: 電話番号
          - generic [ref=e12]:
            - img [ref=e13]
            - textbox "電話番号" [ref=e15]:
              - /placeholder: "09012345678"
        - generic [ref=e16]:
          - generic [ref=e17]: パスワード
          - generic [ref=e18]:
            - img [ref=e19]
            - textbox "パスワード" [ref=e22]:
              - /placeholder: パスワードを入力
        - button "ログイン" [ref=e23] [cursor=pointer]
      - generic [ref=e24]:
        - link "新規登録はこちら" [ref=e25] [cursor=pointer]:
          - /url: /signup
          - paragraph [ref=e26]: 新規登録はこちら
        - link "パスワードをお忘れの方はこちら" [ref=e27] [cursor=pointer]:
          - /url: /password-reset
          - paragraph [ref=e28]: パスワードをお忘れの方はこちら
    - paragraph [ref=e29]: © 2025 OZA. All rights reserved.
  - alert [ref=e30]
```