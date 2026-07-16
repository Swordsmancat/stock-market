# Validate Eastmoney read-only data access

## Goal

Determine whether Eastmoney can add reliable personal-research data beyond the
repository's existing AkShare/Eastmoney-backed fallbacks, while keeping account
credentials and browser sessions out of the application unless a specific
account-only dataset justifies that risk.

## Background

- The product is a personal research workspace. Simplicity, source attribution,
  no fabrication, and read-only behavior are more important than broad account
  automation.
- The user approved a separate feasibility probe after the homepage task; no
  implementation or account-session access has been approved yet.

## Verified Findings

- Bounded public GET probes on 2026-07-16 reached Eastmoney intraday trends,
  stock fund flow, news search, announcements, financial indicators, and
  company-profile data without a Cookie or login.
- Quote, daily K-line, and sector-flow endpoints disconnected before returning
  an HTTP response while related public endpoints remained reachable. This is
  endpoint instability, not evidence that authentication is required.
- The existing repository already accesses Eastmoney-backed daily/minute bars,
  market depth, fund flow, sectors, limit-up rows, Dragon Tiger List, block
  trades, news, fundamentals, the A-share universe, and dividends through
  AkShare. Official disclosures remain on CNINFO.
- Direct Eastmoney access has limited incremental value for news discovery,
  selected fundamentals/company facts, and stock fund flow, but no demonstrated
  value for duplicate quote, K-line, or intraday paths.
- Eastmoney's public legal statement restricts copying and dissemination of
  protected content and exchange market information. Public reachability does
  not establish permission for bulk collection, persistence, or redistribution.
- No indispensable account-only research dataset was identified. Login adds
  private watchlist, portfolio, and account-message access rather than solving
  the current public market-data reliability problem.
- The current JSON settings and network-exposed settings API are not a safe
  storage boundary for bearer session Cookies.

## Requirements

- Inventory current Eastmoney/AkShare code paths, payload provenance, retry and
  validation behavior, and existing credential-redaction conventions.
- Probe only documented or publicly reachable Eastmoney GET surfaces needed to
  assess data categories relevant to the product: quotes/bars, market and fund
  flow, news, announcements, and fundamentals.
- Classify each candidate as public and reusable, public but brittle/licensing
  sensitive, account-only, or unsuitable.
- Identify whether any desired capability actually requires an Eastmoney
  account instead of the existing public/AkShare providers.
- Recommend the smallest provider boundary, rate limit, cache, diagnostics,
  source-attribution, and storage/citation rules for a later implementation.
- Preserve all unrelated dirty files and the normal 3000/8000 services.
- Do not inspect browser cookies or local storage, accept CAPTCHA, save account
  passwords, submit login forms, bypass access controls, or perform any POST,
  watchlist, portfolio, order, or trading action.
- Treat public integration and authenticated-session integration as independent
  decisions. Public reachability must not be used to infer licensing permission.

## Acceptance Criteria

- [x] A task-local report maps current repository coverage to candidate
      Eastmoney data categories and records bounded public GET probe evidence.
- [x] The report clearly separates public data from account-only/private data
      and records access, stability, licensing, and attribution risks.
- [x] The report gives a go/no-go recommendation for public integration and for
      login-session integration independently.
- [x] Any proposed login-session design excludes password capture, CAPTCHA
      automation, cookie scraping from an existing browser profile, and write
      actions; it includes local encryption, explicit import/revocation,
      expiry detection, redaction, and a provider kill switch.
- [x] No application code, database data, browser session, or remote account is
      changed during the feasibility phase.

## Out Of Scope

- Implementing an Eastmoney provider or settings UI.
- Logging into Eastmoney or importing a real session cookie.
- Scraping authenticated HTML, bypassing anti-bot controls, or automating a
  user's Eastmoney watchlist, portfolio, comments, messages, or trades.
- Replacing official exchange, CNINFO, NBS, PBOC, or other authoritative
  evidence sources with an aggregator when the official source is available.

## Decision

- Public integration is conditionally suitable only as a low-frequency,
  personal-local fallback with explicit source attribution, schema validation,
  bounded caching/rate limits, and a provider kill switch. The existing
  AkShare and official-source paths remain preferred.
- Login-session integration is not suitable for the current scope. It may be
  reconsidered only in a separate task after one indispensable account-only
  field is named and public or official alternatives are shown insufficient.
