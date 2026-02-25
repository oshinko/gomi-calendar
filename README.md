# gomi-calendar

市区町村ごとのごみ収集カレンダーを表示する React Router + Vite ベースの静的サイトです。

## Requirements

- Node.js 20+
- npm

## Setup

```bash
npm install
cp .env.example .env
```

`.env`:

```env
VITE_TITLE=ごみ収集カレンダー
```

## Run

```bash
npm run dev
```

Build:

```bash
npm run build
npm run start
```

## Data Files

- `data/municipalities.json`
  - 自治体マスタ（`slug`, `type`, `name`, `wards` など）
- `data/calendars.json`
  - カレンダー実データ
  - `municipality.slug` + `municipality.type` で自治体に紐づけ

`data.ts` で両データを結合し、`municipalities` をアプリ全体に公開しています。

## Routes (Current)

- `/`
  - 自治体一覧
- `/:municipality/:type`
  - 自治体ページ（カレンダー一覧表示）

## Static Prerender

`react-router.config.ts` で prerender を有効化しています。

- `ssr: false`
- `municipalities` から `/{slug}/{type}` を静的生成

## Key Files

- `app/root.tsx`
  - 共通レイアウト
  - `<title>` は `VITE_TITLE`（未設定時は `DEFAULT_TITLE`）
- `app/routes/_index.tsx`
  - 自治体一覧ページ
- `app/routes/$municipality.$type.tsx`
  - 自治体詳細ページ
- `consts.ts`
  - アプリ共通定数
- `scripts/generate_municipalities.py`
  - 自治体データ生成スクリプト

## Notes

- 現在は自治体ページまで実装済みです。
- `/{slug}/{type}/{wardSlug}`（行政区ページ）は未実装です。
