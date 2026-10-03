import { ClaimCard } from '../components/card/ClaimCard.jsx'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'
import supportedContradicts from '../../../contracts/fixtures/supported-contradicts.json'
import disputed from '../../../contracts/fixtures/disputed.json'
import cannotConfirm from '../../../contracts/fixtures/cannot-confirm.json'

// Development-only preview of the card UI, built from synthetic P-07 fixtures. App renders this only
// when import.meta.env.DEV is true, so it never ships in a production build.
const fixtures = [supportedConfirms, supportedContradicts, disputed, cannotConfirm]

export function CardPreview() {
  return (
    <section aria-label={strings.devPreviewBanner}>
      <p className="dev-banner" role="note">
        {strings.devPreviewBanner}
      </p>
      {fixtures.map((card) => (
        <ClaimCard key={card.state_label_key} card={card} />
      ))}
    </section>
  )
}
