# Design Guidelines: Agentic Travel Assistant

## Design Approach

**Reference-Based Strategy**: Drawing inspiration from modern travel platforms (Airbnb, Booking.com) combined with contemporary AI chat interfaces (Linear, ChatGPT) to create a conversational travel experience that feels both intelligent and approachable.

**Core Principles**:
- Conversational clarity over visual noise
- Structured data presentation within natural dialogue
- Progressive disclosure of complex flight information
- Mobile-first responsive chat experience

---

## Typography Hierarchy

**Primary Font**: Inter or similar geometric sans-serif for excellent readability at all sizes
**Secondary Font**: Same family with weight variations for hierarchy

**Scale**:
- Chat messages: text-sm to text-base (14-16px)
- Flight card headlines: text-lg to text-xl (18-20px)
- Section headers: text-2xl to text-3xl (24-30px)
- User input: text-base (16px) - critical for mobile keyboards
- Timestamps/metadata: text-xs (12px)

**Weights**: 
- Regular (400) for body text and messages
- Medium (500) for flight prices and key data points
- Semibold (600) for headers and primary CTAs
- Bold (700) for emphasis within flight cards

---

## Layout System

**Spacing Primitives**: Use Tailwind units of 2, 4, 6, and 8 for consistency
- Component padding: p-4 to p-6
- Section spacing: space-y-6 to space-y-8
- Card gaps: gap-4
- Message bubbles: p-4 with rounded-2xl
- Flight card internal spacing: p-6

**Container Strategy**:
- Chat container: max-w-4xl centered
- Flight result cards: max-w-3xl within chat flow
- Sidebar (preferences): w-80 on desktop, full-width drawer on mobile
- Input area: Fixed to bottom with max-w-4xl

**Responsive Breakpoints**:
- Mobile-first with single-column chat
- md: Two-column layout (chat + optional sidebar)
- lg: Wider flight cards with multi-column data display

---

## Component Library

### Chat Interface

**Message Structure**:
- User messages: Right-aligned, distinct container style, max-w-2xl
- Assistant messages: Left-aligned, full-width when containing flight results, otherwise max-w-2xl
- System messages: Centered, subtle styling for timestamps/status updates

**Message Layout**:
- Avatar (32px) + content area
- Timestamp below message in text-xs
- Streaming indicator (3 animated dots) during AI responses
- Smooth scroll-to-bottom on new messages

**Input Area**:
- Fixed bottom position with backdrop blur
- Expandable textarea (1-4 lines)
- Send button (always visible)
- Character counter for long inputs
- Suggested quick actions as chips above input

### Flight Result Cards

**Card Structure** (within assistant messages):
- Header: Airline logo + flight number + departure/arrival times
- Visual timeline: Dots connected by line showing route with stops
- Middle section: Duration, stops, layover times in columns
- Price section: Large price display + cabin class badge
- Footer: Comparison tags (e.g., "Fastest option", "Best value")
- Action button: "Select" or "View details"

**Layout Grid** (within card):
- Desktop: 3-column grid for flight details (departure | route info | arrival)
- Mobile: Stacked vertical layout with clear dividers
- Price always prominent (text-2xl, semibold)

**Comparison View**:
- When showing multiple flights, use vertical stack with gap-4
- Highlight badges: Small pills showing "Cheapest", "Fastest", "Recommended"
- Quick compare button to show side-by-side overlay

### Navigation & Header

**Top Bar**:
- Logo/brand (left)
- User profile avatar (right)
- Settings/preferences icon
- Height: h-16 with border-bottom divider

**Preferences Sidebar** (optional, desktop):
- Slide-out panel from right
- Sections: Saved preferences, Travel history, Account settings
- Toggle switches for preferences (direct flights, avoid red-eyes)
- Saved airlines as removable chips

### Interactive Elements

**Buttons**:
- Primary CTA: rounded-lg, px-6, py-3, medium weight
- Secondary: outlined variant with same padding
- Text buttons: for less critical actions (px-4, py-2)

**Form Inputs** (for filters/refinement):
- Date picker: Calendar overlay with range selection
- Passenger selector: Dropdown with increment/decrement controls
- Cabin class: Radio button group with visual icons
- All inputs: rounded-lg with consistent h-12 height

**Chips/Tags**:
- Removable preference tags: rounded-full, px-4, py-2, with × icon
- Filter badges: Similar style, non-removable
- Airline logos: Circular, 24px for inline, 40px for cards

---

## Images

**Hero Section**: Not applicable - this is a chat-first application, no traditional landing page hero

**In-Chat Imagery**:
- **Airline Logos**: 40x40px circular containers within flight cards, sourced from airline brand assets
- **Empty State Illustration**: Friendly travel-themed illustration (airplane, globe) when chat is empty, approximately 200px wide, centered above welcome message
- **Destination Thumbnails** (optional): Small 80x80px rounded images next to flight results showing destination city
- **Loading States**: Subtle animated plane icon (32px) during API calls

**Profile/Preferences**:
- User avatar: 40px circular in header, 80px in profile view
- Placeholder: Initials on geometric background if no photo

---

## Specific Patterns

**Multi-turn Conversation Flow**:
- Clear visual separation between turns (space-y-6)
- Context retention shown via subtle reference ("As you mentioned earlier...")
- Edit previous message: Hover state reveals edit icon on user messages

**Memory Indicators**:
- When AI uses stored preference, show small chip: "Using your preference: Direct flights only"
- Inline within assistant message, subtle styling

**Error Handling**:
- Inline error messages in assistant bubble with warning icon
- Retry button within error message
- Graceful degradation for API failures

**Loading States**:
- Skeleton screens for flight cards while searching
- Pulsing animation on card placeholders
- Progress indicator for multi-step searches

**Accessibility**:
- Focus visible states for all interactive elements
- ARIA labels for icon-only buttons
- Keyboard navigation through chat history and flight cards
- Screen reader announcements for new messages

---

## Animation Principles

**Use Sparingly**:
- Smooth scroll when new messages appear (300ms ease)
- Fade-in for new flight cards (200ms)
- Slide-up for input suggestions
- No page transitions - instant navigation
- Avoid parallax, complex hover effects, or decorative animations