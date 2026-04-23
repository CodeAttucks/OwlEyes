'use client'

import { Fragment } from 'react'
import { Menu, Transition } from '@headlessui/react'
import { GlobeAltIcon } from '@heroicons/react/24/outline'
import { useI18n, SUPPORTED_LOCALES, LOCALE_LABELS, type Locale } from '../lib/i18n'

export default function LanguageSwitcher() {
  const { locale, setLocale } = useI18n()

  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
        aria-label="Select language"
      >
        <GlobeAltIcon className="w-4 h-4" aria-hidden="true" />
        <span className="uppercase">{locale}</span>
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-10 mt-1 w-40 origin-top-right rounded-lg bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="py-1">
            {SUPPORTED_LOCALES.map((code) => (
              <Menu.Item key={code}>
                {({ active }) => (
                  <button
                    onClick={() => setLocale(code as Locale)}
                    className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between ${
                      active ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700'
                    } ${locale === code ? 'font-semibold' : ''}`}
                  >
                    {LOCALE_LABELS[code as Locale]}
                    {locale === code && <span className="text-indigo-600">✓</span>}
                  </button>
                )}
              </Menu.Item>
            ))}
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  )
}
