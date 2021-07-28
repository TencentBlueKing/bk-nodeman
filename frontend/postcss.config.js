/* eslint-disable @typescript-eslint/no-require-imports */
const cssImport = require('postcss-import')
const createResolver = require('postcss-import-webpack-resolver')
const path = require('path')
// const baseConf = require('./build/webpack.base.conf.js')

const postcssPlugins = [
  cssImport({
    resolve: createResolver({
      alias: {
        vue$: 'vue/dist/vue.esm.js',
        '@': path.resolve('src')
      },
      modules: ['src', 'node_modules']
    })
  })
]
module.exports = {
  // You can specify any options from http://api.postcss.org/global.html#processOptions here
  plugins: [
    // Plugins for PostCSS

    ...postcssPlugins,
    // mixins，本插件需要放在 postcss-simple-vars 和 postcss-nested 插件前面
    // @see https://github.com/postcss/postcss-mixins#postcss-mixins-
    ['postcss-mixins'],
    ['postcss-url', { url: 'rebase' }],
    ['postcss-preset-env', {
      stage: 0,
      autoprefixer: {
        grid: true
      }
    }],
    ['postcss-nested'],
    ['postcss-atroot'],
    ['postcss-extend-rule'],
    ['postcss-advanced-variables'],
    ['postcss-property-lookup']
  ]
}
