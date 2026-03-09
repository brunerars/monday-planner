import useScrollReveal from '../hooks/useScrollReveal'
import Nav         from '../components/landing/Nav'
import Hero        from '../components/landing/Hero'
import Ticker      from '../components/landing/Ticker'
import HowItWorks  from '../components/landing/HowItWorks'
import Benefits    from '../components/landing/Benefits'
import CtaSection  from '../components/landing/CtaSection'
import Footer      from '../components/landing/Footer'

export default function LandingPage() {
  useScrollReveal()

  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Ticker />
        <HowItWorks />
        <Benefits />
        <CtaSection />
      </main>
      <Footer />
    </>
  )
}
