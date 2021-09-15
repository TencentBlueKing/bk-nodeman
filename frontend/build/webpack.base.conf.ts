import webpack from 'webpack'
import CopyWebpackPlugin from 'copy-webpack-plugin'
// import friendlyFormatter from 'eslint-friendly-formatter'
import { resolve, assetsPath } from './util'
import config from './config'
import ProgressBarPlugin from 'progress-bar-webpack-plugin'
import VueLoaderPlugin from 'vue-loader/lib/plugin'
import chalk from 'chalk'
import os from 'os'

const isProd = process.env.NODE_ENV === 'production'

const baseConfig: webpack.Configuration = {
  output: {
    path: isProd ? config.build.assetsRoot : resolve(config.dev.assetsRoot),
    filename: '[name].js',
    publicPath: isProd ? config.build.assetsPublicPath : config.dev.assetsPublicPath,
    // chunkLoading: false,
    // wasmLoading: false
  },

  target: 'web',

  stats: 'verbose',

  resolve: {
    // 指定以下目录寻找第三方模块，避免 webpack 往父级目录递归搜索，
    // 默认值为 ['node_modules']，会依次查找./node_modules、../node_modules、../../node_modules
    modules: [resolve('src'), resolve('node_modules')],
    extensions: ['.js', '.vue', '.json', '.ts', 'tsx'],
    alias: {
      vue$: 'vue/dist/vue.esm.js',
      '@': resolve('src')
    }
  },

  module: {
    noParse: [
      /\/node_modules\/jquery\/dist\/jquery\.min\.js$/,
      /\/node_modules\/echarts\/dist\/echarts\.min\.js$/
    ],
    rules: [
      // {
      //     test: /\.(js|vue)$/,
      //     loader: 'eslint-loader',
      //     enforce: 'pre',
      //     include: [resolve('src'), resolve('test'), resolve('static')],
      //     exclude: /node_modules/,
      //     options: {
      //         formatter: friendlyFormatter
      //     }
      // },
      {
        test: /\.vue$/,
        include: resolve('src'),
        use: {
          loader: 'vue-loader',
          options: {
            transformAssetUrls: {
              video: 'src',
              source: 'src',
              img: 'src',
              image: 'xlink:href'
            }
          }
        }
      },
      {
        oneOf: [
          {
            test: /\.js$/,
            include: resolve('src'),
            exclude: /node_modules/,
            use: [
              {
                loader: 'thread-loader',
                options: {
                  workers: os.cpus().length - 1
                }
              },
              {
                loader: 'babel-loader',
                options: {
                  // include: [resolve('src')],
                  cacheDirectory: './webpack_cache/',
                  // 确保 JS 的转译应用到 node_modules 的 Vue 单文件组件
                  // exclude: (file: string) => (
                  //   /node_modules/.test(file) && !/\.vue\.js/.test(file)
                  // )
                }
              }
            ]
          },
          {
            test: /\.tsx?$/,
            include: resolve('src'),
            exclude: /node_modules/,
            use: [
              {
                loader: 'babel-loader',
                options: {
                  cacheDirectory: './webpack_cache/'
                }
              },
              {
                loader: 'ts-loader',
                options: {
                  transpileOnly: true,
                  appendTsxSuffixTo: [/\.vue$/]
                }
              }
            ]
          },
          {
            test: /\.(png|jpe?g|gif|svg)(\?.*)?$/,
            loader: 'url-loader',
            options: {
              limit: 10000,
              name: assetsPath('images/[name].[hash:7].[ext]'),
              esModule: false
            }
          },
          {
            test: /\.(mp4|webm|ogg|mp3|wav|flac|aac)(\?.*)?$/,
            use: {
              loader: 'url-loader',
              options: {
                limit: 10000,
                name: assetsPath('media/[name].[hash:7].[ext]')
              }
            }
          },
          {
            test: /\.(woff2?|eot|ttf|otf)(\?.*)?$/,
            use: {
              loader: 'url-loader',
              options: {
                limit: 10000,
                name: assetsPath('fonts/[name].[hash:7].[ext]')
              }
            }
          },
          {
            test: /.md$/,
            use: [
              {
                loader: 'vue-loader'
              },
              {
                loader: 'vue-markdown-loader/lib/markdown-compiler',
                options: {
                  raw: true
                }
              }
            ]
          }
        ]
      }
    ]
  },

  plugins: [
    new VueLoaderPlugin(),
    // moment 优化，只提取本地包
    new webpack.ContextReplacementPlugin(/moment\/locale$/, /zh-cn/),
    new CopyWebpackPlugin({
      patterns: [{
        from: resolve('static/images'),
        to: resolve('dist/static/images'),
        toType: 'dir'
      }]
    }),
    new ProgressBarPlugin({
      format: '  build [:bar] ' + chalk.green.bold(':percent') + ' (:elapsed seconds)',
      clear: false,
      total: 0
    })
  ]
}

export default baseConfig
