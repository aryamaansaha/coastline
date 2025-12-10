# Components

Reusable UI components, props, and styling.

## Overview

Components are organized in `src/components/` with paired CSS Module files.

```
src/components/
├── ActivityCard.tsx       + .module.css
├── BudgetBar.tsx          + .module.css
├── ConfirmModal.tsx       + .module.css
├── DaySection.tsx         + .module.css
├── DiscoveryDrawer.tsx    + .module.css
├── Logo.tsx               + .module.css
├── RevisionModal.tsx      + .module.css
├── TripMap.tsx            + .module.css
└── index.ts               # Barrel export
```

---

## ActivityCard

Displays a single activity within a day section.

### Props

```typescript
interface ActivityCardProps {
  activity: Activity;
  isHighlighted?: boolean;
  showDiscovery?: boolean;
  onDiscoveryClick?: () => void;
  onClick?: () => void;
}
```

### Usage

```tsx
<ActivityCard
  activity={activity}
  isHighlighted={selectedActivity?.id === activity.id}
  showDiscovery={true}
  onDiscoveryClick={() => handleDiscovery(activity)}
  onClick={() => setSelected(activity)}
/>
```

### Features

- Activity type icon (flight ✈️, hotel 🏨, activity 🎯)
- Time slot display
- Title and description
- Location name
- Estimated cost
- "Find Nearby" button (optional)
- Highlight state for selected

---

## BudgetBar

Visual budget progress indicator.

### Props

```typescript
interface BudgetBarProps {
  totalCost: number;
  budgetLimit: number;
}
```

### Usage

```tsx
<BudgetBar totalCost={2450} budgetLimit={3000} />
```

### Features

- Progress bar showing cost vs budget
- Color coding: green (under), yellow (near), red (over)
- Dollar amounts displayed
- Percentage indicator

---

## ConfirmModal

Generic confirmation dialog replacing browser `confirm()`.

### Props

```typescript
interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel?: () => void;
  confirmLabel?: string;    // Default: "Confirm"
  cancelLabel?: string;     // Default: "Cancel"
  isLoading?: boolean;
  variant?: 'danger' | 'warning' | 'info' | 'success';
}
```

### Usage

```tsx
<ConfirmModal
  isOpen={deleteModal !== null}
  title="Delete Trip?"
  message="This cannot be undone."
  confirmLabel="Delete"
  variant="danger"
  onConfirm={handleDelete}
  onCancel={() => setDeleteModal(null)}
/>
```

### Features

- Overlay with backdrop click to close
- Escape key closes modal
- Variant-based styling (colors, icons)
- Loading state for async actions

---

## DaySection

Groups activities by day with header.

### Props

```typescript
interface DaySectionProps {
  day: Day;
  highlightedActivityId?: string;
  showDiscovery?: boolean;
  onDiscoveryClick?: (activity: Activity) => void;
  onActivityClick?: (activity: Activity) => void;
}
```

### Usage

```tsx
{trip.days.map((day, index) => (
  <DaySection
    key={day.id || `day-${day.day_number}-${index}`}
    day={day}
    highlightedActivityId={selectedActivity?.id}
    showDiscovery={true}
    onDiscoveryClick={handleDiscoveryClick}
    onActivityClick={setSelectedActivity}
  />
))}
```

### Features

- Day header with number, city, theme
- List of ActivityCard components
- Passes discovery/click handlers down

---

## DiscoveryDrawer

Slide-out panel for discovering nearby places.

### Props

```typescript
interface DiscoveryDrawerProps {
  activity: Activity;
  tripId: string;
  onClose: () => void;
  onDiscover: (activityId: string, type: DiscoveryType, regenerate: boolean) => Promise<DiscoveredPlace[]>;
  onStar: (activityId: string, type: DiscoveryType, placeId: string, starred: boolean) => Promise<void>;
  discoveries: Partial<Record<DiscoveryType, DiscoveredPlace[]>>;
}
```

### Usage

```tsx
{discoveryOpen && selectedActivity && (
  <DiscoveryDrawer
    activity={selectedActivity}
    tripId={tripId}
    onClose={() => setDiscoveryOpen(false)}
    onDiscover={handleDiscover}
    onStar={handleStar}
    discoveries={discoveryCache[selectedActivity.id] || {}}
  />
)}
```

### Features

- Tabs for place types (restaurant, bar, cafe, club)
- "Find" button for initial discovery
- Place cards with star/unstar
- Refresh/regenerate button
- Google Maps links
- Loading and empty states

### Sub-component: PlaceCard

```typescript
interface PlaceCardProps {
  place: DiscoveredPlace;
  onStar: (starred: boolean) => void;
}
```

---

## Logo

Application logo component.

### Props

```typescript
interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}
```

### Usage

```tsx
<Logo size="lg" />
<Logo size="md" onClick={() => navigate('/')} />
```

### Features

- Three size variants
- Optional click handler
- Uses `logo.png` from assets

---

## RevisionModal

Modal for submitting revision feedback.

### Props

```typescript
interface RevisionModalProps {
  currentBudget: number;
  onSubmit: (feedback: string, newBudget?: number) => void;
  onCancel: () => void;
}
```

### Usage

```tsx
{showRevisionModal && (
  <RevisionModal
    currentBudget={budget_limit}
    onSubmit={handleRevise}
    onCancel={() => setShowRevisionModal(false)}
  />
)}
```

### Features

- Text area for feedback
- Optional budget increase field
- Submit/Cancel buttons

---

## TripMap

Interactive Leaflet map showing activity locations.

### Props

```typescript
interface TripMapProps {
  activities: Activity[];
  selectedActivity?: Activity | null;
  onActivitySelect?: (activity: Activity) => void;
  fallbackCities?: string[];  // For preview mode
}
```

### Usage

```tsx
<TripMap
  activities={allActivities}
  selectedActivity={selectedActivity}
  onActivitySelect={setSelectedActivity}
  fallbackCities={['London', 'Paris']}
/>
```

### Features

- Auto-fit bounds to markers
- Fly to selected activity
- Click markers to select
- Popup with activity info
- Preview mode (no markers, city-centered)
- Fallback coordinates for common cities

### Sub-components

- `FitBounds` - Auto-fits map to markers
- `FlyToSelected` - Animates to selected marker
- `SetViewOnMount` - Initial view setup

### City Coordinates Fallback

```typescript
const CITY_COORDS: Record<string, [number, number]> = {
  'london': [51.5074, -0.1278],
  'paris': [48.8566, 2.3522],
  // ... more cities
};
```

---

## Styling Patterns

### CSS Module Import

```tsx
import styles from './ComponentName.module.css';

<div className={styles.container}>
```

### Conditional Classes

```tsx
<div className={`${styles.card} ${isActive ? styles.active : ''}`}>
```

### Global Variables

All components use CSS variables from `index.css`:

```css
:root {
  --primary: #0f172a;
  --primary-light: #e0f2fe;
  --text: #0f172a;
  --text-muted: #64748b;
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
}
```

---

## Icon Usage

Components use **Lucide React** icons:

```tsx
import { ArrowLeft, Star, MapPin, Loader } from 'lucide-react';

<ArrowLeft size={18} />
<Star size={16} fill={starred ? 'currentColor' : 'none'} />
```

Common icons:
- Navigation: `ArrowLeft`, `ChevronRight`, `X`
- Status: `Loader`, `RefreshCw`, `Check`
- Actions: `Trash2`, `Edit2`, `Star`, `Search`
- Content: `MapPin`, `Calendar`, `Wallet`, `Plane`

---

## Barrel Export

`src/components/index.ts` exports all components:

```typescript
export { ActivityCard } from './ActivityCard';
export { BudgetBar } from './BudgetBar';
export { ConfirmModal } from './ConfirmModal';
export { DaySection } from './DaySection';
export { DiscoveryDrawer } from './DiscoveryDrawer';
export { Logo } from './Logo';
export { RevisionModal } from './RevisionModal';
export { TripMap } from './TripMap';
```

---

## Related

- [PAGES.md](./PAGES.md) - Page-level usage
- [DISCOVERY.md](./DISCOVERY.md) - DiscoveryDrawer details
- [TYPES.md](./TYPES.md) - TypeScript interfaces

