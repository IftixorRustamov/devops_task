"""auth-service: foydalanuvchilar, rollar, JWT va refresh tokenlar.

Egasi bo‘lgan baza: auth-db (users, refresh_tokens).
JWT imzo kaliti faqat shu servisda. Gateway har bir himoyalangan so‘rovni
`GET /internal/verify` orqali tekshiradi.
"""
