import { useLang } from '../hooks/useLang.jsx'
import { Reveal, RichText, SectionHead } from './primitives.jsx'

const QUESTIONS = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7']

export function Faq () {
  const { t } = useLang()

  return (
    <section className='faq' id='faq'>
      <SectionHead
        tag={t('faq.tag')}
        title={t('faq.title1')}
        accent={t('faq.title2')}
      />

      <div className='faq-grid'>
        {QUESTIONS.map(n => (
          <Reveal as='details' className='faq-item' key={n}>
            <summary>
              <span>
                <RichText text={t(`faq.${n}`)} />
              </span>
            </summary>
            <p>
              <RichText text={t(`faq.a${n.slice(1)}`)} />
            </p>
          </Reveal>
        ))}
      </div>
    </section>
  )
}
