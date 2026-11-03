# AI DEVELOPMENT INSTRUCTIONS — RESPONSIVE ENTERPRISE APPLICATION

## 1. Responsive Architecture
- اعتبر Responsive Design جزءًا أساسيًا من Architecture.
- استخدم Mobile-First / Responsive-First.
- لا تنشئ نسخة منفصلة للموبايل أو التابلت أو سطح المكتب.
- استخدم نفس Codebase لجميع الأجهزة.

## 2. Device & Screen Support
- دعم جميع الأحجام من 320px حتى Ultra-Wide.
- دعم Mobile, Tablet, Laptop, Desktop.
- لا تعتمد على مقاس جهاز محدد.
- استخدم Breakpoints مرنة مثل:
  - xs < 576px
  - sm ≥ 576px
  - md ≥ 768px
  - lg ≥ 992px
  - xl ≥ 1200px
  - xxl ≥ 1400px

## 3. Responsive CSS
- استخدم Mobile-First CSS.
- استخدم:
  - Flexbox
  - CSS Grid
  - `width: 100%`
  - `max-width`
  - `min-width`
  - `clamp()`
  - CSS Media Queries
- تجنب Fixed Width غير الضروري.
- تجنب Fixed Position وAbsolute Positioning إلا عند الحاجة.
- لا تستخدم `width: 1200px` كحل أساسي.

## 4. Layout
- استخدم:
  `Container → Grid/Row → Columns → Components`
- يجب أن يتكيف Layout تلقائيًا مع حجم الشاشة.
- امنع أي Horizontal Overflow غير ضروري.

## 5. Navigation & Sidebar
- Desktop: Sidebar كامل.
- Tablet: Sidebar مصغر أو Icons.
- Mobile: Drawer / Offcanvas.
- Navbar يجب أن يتكيف تلقائيًا.
- ممنوع:
  - Text Overlap
  - Icons خارج الشاشة
  - Navbar أكبر من الشاشة
  - Horizontal Overflow

## 6. Tables
- الجداول يجب أن تكون Responsive.
- على Mobile استخدم أحد الحلول:
  - Horizontal Scroll
  - تحويل الصفوف إلى Cards
- لا تسمح للجدول بكسر الصفحة.

## 7. Forms
- Desktop: Multi-Column عند الحاجة.
- Mobile: تتحول الحقول إلى Single Column.
- جميع الحقول والأزرار يجب أن تكون Touch Friendly.

## 8. Buttons & Touch
- استخدم Touch Targets مناسبة للموبايل.
- لا تعتمد على Hover لتنفيذ وظائف أساسية.
- أي وظيفة تعمل بالـHover يجب أن يكون لها بديل للموبايل.
- دعم Swipe / Scroll / Mobile Dropdown / Mobile Modal عند الحاجة.

## 9. Modals
- Modal يجب ألا يتجاوز شاشة الهاتف.
- استخدم:
  - `width: 100%`
  - `max-width`
  - `max-height`
  - `overflow-y: auto`

## 10. Dashboard & Cards
- Dashboard يجب أن يتكيف تلقائيًا.
- Cards يجب أن تستخدم Responsive Grid.
- استخدم `auto-fit` و`minmax()` عند الحاجة.
- لا تستخدم Fixed Card Width.

## 11. Typography
- استخدم Typography Responsive.
- استخدم `clamp()` للعناوين والأحجام الكبيرة.
- حافظ على Readability في جميع الشاشات.

## 12. RTL / LTR
- النظام يجب أن يدعم RTL وLTR بشكل كامل.
- العربية → RTL.
- الإنجليزية → LTR.
- استخدم CSS Logical Properties مثل:
  - `margin-inline`
  - `padding-inline`
  - `inset-inline`
  - `border-inline`
  - `text-align: start`
- تجنب الاعتماد المفرط على `left/right`.

## 13. Images & Media
- الصور يجب ألا تكسر Layout.
- استخدم:
  `max-width: 100%; height: auto;`
- طبّق ذلك على Logos, Avatars, Products, Attachments, Documents.

## 14. Charts & Reports
- Charts يجب أن تكون Responsive.
- يجب أن تتكيف:
  - Width
  - Height
  - Labels
  - Legend
  - Tooltip
- Reports وPrint Views يجب أن تدعم A4/A5 وPortrait/Landscape.

## 15. Accessibility
- التزم بمبادئ WCAG.
- دعم:
  - Keyboard Navigation
  - Focus States
  - Screen Readers
  - Semantic HTML
  - Labels
  - ARIA عند الحاجة
  - Color Contrast
  - Accessible Forms
  - Accessible Buttons
- لا تعتمد على اللون وحده لنقل المعلومات.

## 16. Browser Compatibility
اختبر النظام على:
- Chrome
- Edge
- Firefox
- Safari
- iOS Safari
- Android Chrome
- Samsung Internet
- Edge Mobile

استخدم Fallback عند الحاجة.

## 17. Mobile Browser
يجب مراعاة:
- Safe Area
- Viewport
- Virtual Keyboard
- Browser Address Bar
- Orientation Changes
- Portrait / Landscape

واستخدم Viewport Meta Tag الصحيح.

## 18. Performance
Responsive لا يعني تغيير الحجم فقط.

استخدم عند الحاجة:
- Lazy Loading
- Image Optimization
- Minification
- Compression
- Efficient CSS
- Efficient JavaScript
- Pagination
- API Pagination
- Browser Caching

ولا تحمل ملفات غير ضرورية على Mobile.

## 19. Component-Based UI
كل Component يجب أن يكون Responsive، بما في ذلك:
- Buttons
- Inputs
- Selects
- Tables
- Cards
- Modals
- Dropdowns
- Navbar
- Sidebar
- Alerts
- Toasts
- Tabs
- Pagination
- Breadcrumbs
- Forms
- Charts

لا تنشئ Component يعمل على Desktop فقط.

## 20. Design System
استخدم Design System موحد يشمل:
- Colors
- Typography
- Spacing
- Buttons
- Forms
- Cards
- Tables
- Alerts
- Modals
- Navigation
- Icons

ويجب أن يكون Responsive وRTL/LTR Compatible.

## 21. CSS Architecture
نظّم CSS بشكل Modular وقابل للصيانة.

افصل على الأقل بين:
- Base
- Layout
- Components
- Responsive

لا تضع جميع CSS في ملف واحد ضخم.

## 22. Responsive Testing
اختبر كل Page على الأقل على:
- 320px
- 360px
- 390px
- 414px
- 768px
- 1024px
- 1366px
- 1920px

وتأكد من عدم وجود:
- Overflow
- Overlap
- Broken Layout
- Hidden Actions
- Unusable Forms
- Unreadable Text
- Broken Tables

## 23. Quality Gate
قبل اعتماد أي Page أو Module جديد، تحقق من:
- Navigation
- Sidebar
- Forms
- Tables
- Cards
- Buttons
- Modals
- Charts
- Search
- Filters
- Pagination
- RTL
- LTR
- Touch
- Keyboard
- Accessibility
- Responsive behavior

## 24. Mandatory Rule
كل:
- Page
- View
- Template
- Component
- Form
- Table
- Dashboard
- Modal
- Report
- Chart

يجب أن يكون:

**Responsive + Accessible + RTL/LTR + Touch Friendly + Mobile Friendly + Desktop Optimized**

## 25. Final AI Rule
لا تعتبر المهمة مكتملة إلا إذا كان النظام يعمل من نفس Codebase على:

**Mobile → Tablet → Laptop → Desktop → Ultra-Wide**

وعلى:

**Android → iPhone → iPad → Windows → macOS → Linux**

بدون إنشاء نسخ منفصلة للأجهزة.

### أهم قاعدة:
**Responsive Design Requirement إلزامي وليس Feature إضافية.**

أي كود جديد يجب أن يكون:
**Responsive, Accessible, RTL/LTR, Touch Friendly, Performant, Component-Based, Scalable, Maintainable.**