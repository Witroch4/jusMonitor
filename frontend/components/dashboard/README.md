# Dashboard Components

This directory contains the components for the Central Operacional (Dashboard) page.

## Components

### UrgentCases
Displays cases with deadlines approaching (< 3 days).
- Shows client name, CNJ number, case type
- Badge with days remaining
- Color-coded urgency (red for 1 day, default for 2-3 days)
- Links to client profile

### AttentionCases
Displays cases that haven't had movement in > 30 days.
- Shows client name, CNJ number, status
- Badge with days since last movement
- Links to client profile

### GoodNews
Displays favorable decisions and positive movements.
- Shows client name, CNJ number
- AI-generated summary when available
- Green-themed UI for positive reinforcement
- Links to client profile

### Noise
Displays low-priority, irrelevant movements.
- Shows client name, CNJ number, description
- "Mark as read" functionality to hide items
- Gray-themed UI to indicate low priority
- Links to client profile

### Metrics
Displays office KPIs with trend comparisons.
- Conversion rate (lead to client)
- Average response time
- Client satisfaction score
- Total active cases and clients
- Comparison with previous period (% change)
- Trend indicators (up/down arrows)

## Features

### Real-time Updates
- Auto-refresh every 60 seconds (configurable)
- Can be toggled on/off
- Shows notification when new data is available
- Silent background updates

### Filters
- Period selection (7, 30, 60, 90 days)
- Assigned lawyer filter (optional)
- Filters apply to all dashboard sections

### Loading States
- Skeleton loading for all components
- Smooth transitions
- No layout shift during loading

### Responsive Design
- Mobile-first approach
- Grid layout adapts to screen size
- Touch-friendly interactions

## API Integration

All components fetch data from the backend API:
- `/api/v1/dashboard/urgent` - Urgent cases
- `/api/v1/dashboard/attention` - Cases needing attention
- `/api/v1/dashboard/good-news` - Good news
- `/api/v1/dashboard/noise` - Noise
- `/api/v1/dashboard/metrics` - Office metrics

## Usage

```tsx
import { UrgentCases } from '@/components/dashboard/UrgentCases'

<UrgentCases cases={urgentCases} isLoading={isLoading} />
```

## Future Enhancements

- [ ] WebSocket/SSE for true real-time updates
- [ ] Push notifications for urgent cases
- [ ] Export dashboard data to PDF
- [ ] Customizable dashboard layout
- [ ] More granular filters (court, case type, etc.)
- [ ] Charts and visualizations for metrics
