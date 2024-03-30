/** @type {import('tailwindcss').Config} */

const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  mode: "jit",
  content: ["./web/ui/*.html"],
  theme: {
    extend: {},
    screens: {
      'xs': '480px',
      ...defaultTheme.screens,
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

