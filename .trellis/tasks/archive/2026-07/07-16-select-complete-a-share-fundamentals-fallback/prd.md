# Select Complete A-share Fundamentals Fallback

## Goal

Improve personal instrument and AI-research completeness by selecting the most
complete coherent fundamentals snapshot available for an exact A-share symbol.

## Background

- The stored `000001` snapshot contains only debt-to-assets after missing-value
  normalization.
- A sanitized live Eastmoney public read for the same request returned one
  coherent 2026-03-31 snapshot with revenue growth, net margin, and
  debt-to-assets.
- Current behavior always returns stored financial metrics and uses Eastmoney
  only for company context, so available public metrics are discarded.

## Requirements

- Keep complete stored snapshots as zero-network authoritative reads.
- For an eligible exact six-digit A-share with a partial stored snapshot, read
  the bounded cached/public Eastmoney fundamentals projection once.
- Compare whole-snapshot metric completeness across PE, revenue growth, net
  margin, and debt-to-assets. Use the public snapshot only when it has strictly
  more non-null metrics; never merge fields across report dates.
- Preserve the selected snapshot's provider, report date, diagnostics, company
  context, and citation.
- Provider failure, no-data, or an equal/worse public snapshot must retain the
  stored payload and existing company-only fallback behavior.
- The read path must remain Cookie-free, credential-free, bounded, cached, and
  free of ORM writes.
- Keep homepage, ingestion, scheduler, thresholds, assistant invocation,
  watchlist state, portfolio, orders, and trading behavior unchanged.

## Acceptance Criteria

- [x] A regression proves a partial database snapshot selects a strictly more
  complete coherent public snapshot without stitching fields or writing rows.
- [x] Complete, equal-completeness, no-data, and provider-failure cases retain
  the stored snapshot with the existing bounded company behavior.
- [x] `000001` detail displays public revenue growth, net margin, and
  debt-to-assets with public provenance and only PE unavailable.
- [x] Focused/full Python and Web tests, Ruff, TypeScript, Trellis validation,
  and a sanitized browser/API acceptance pass succeed.
