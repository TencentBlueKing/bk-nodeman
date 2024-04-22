import path from 'path'
import webpack from 'webpack'
import merge from 'webpack-merge'
import HtmlWebpackPlugin from 'html-webpack-plugin'
// import AnalyzerPlugin from 'webpack-bundle-analyzer'
// import FriendlyErrorsPlugin from 'friendly-errors-webpack-plugin'

import config from './config'
import baseConf from './webpack.base.conf'
import manifest from '../static/lib-manifest.json'

const webpackConfig = merge(baseConf, {
    mode: 'development',
    devtool: 'eval-source-map',
    entry: {
        main: './src/main.ts'
    },
    output: {
        pathinfo: false
    },
    // optimization: {
    //     runtimeChunk: true,
    //     removeAvailableModules: false,
    //     removeEmptyChunks: false,
    //     splitChunks: false
    // },
    optimization: {
        chunkIds: 'named',
        splitChunks: {
            // 表示从哪些 chunks 里面提取代码，除了三个可选字符串值 initial、async、all 之外，还可以通过函数来过滤所需的 chunks
            // async: 针对异步加载的 chunk 做分割，默认值
            // initial: 针对同步 chunk
            // all: 针对所有 chunk
            chunks: 'all',
            // 表示提取出来的文件在压缩前的最小大小，默认为 30kb
            minSize: 30000,
            // 表示提取出来的文件在压缩前的最大大小，默认为 0，表示不限制最大大小
            maxSize: 1000 * 1024 * 5,
            // 表示被引用次数，默认为 1
            minChunks: 1,
            // 最多有 5 个异步加载请求该 module
            maxAsyncRequests: 5,
            // 初始化的时候最多有 3 个请求该 module
            maxInitialRequests: 3,
            // 名字中间的间隔符
            automaticNameDelimiter: '~',
            // 要切割成的每一个新 chunk 就是一个 cache group，缓存组会继承 splitChunks 的配置，但是 test, priorty 和 reuseExistingChunk 只能用于配置缓存组。
            // test: 和 CommonsChunkPlugin 里的 minChunks 非常像，用来决定提取哪些 module，可以接受字符串，正则表达式，或者函数
            //      函数的一个参数为 module，第二个参数为引用这个 module 的 chunk（数组）
            // priority: 表示提取优先级，数字越大表示优先级越高。因为一个 module 可能会满足多个 cacheGroups 的条件，那么提取到哪个就由权重最高的说了算；
            //          优先级高的 chunk 为被优先选择，优先级一样的话，size 大的优先被选择
            // reuseExistingChunk: 表示是否使用已有的 chunk，如果为 true 则表示如果当前的 chunk 包含的模块已经被提取出去了，那么将不会重新生成新的。
            cacheGroups: {
                // 提取 chunk-bk-magic-vue 代码块
                bkMagic: {
                    chunks: 'all',
                    // 单独将 bkMagic 拆包
                    name: 'chunk-bk-magic-vue',
                    // 权重
                    priority: 5,
                    // 表示是否使用已有的 chunk，如果为 true 则表示如果当前的 chunk 包含的模块已经被提取出去了，那么将不会重新生成新的。
                    reuseExistingChunk: true,
                    test: (module: any) => {
                        return /bk-magic-vue/.test(module.context)
                    }
                },
                // 所有 node_modules 的模块被不同的 chunk 引入超过 1 次的提取为 twice
                // 如果去掉 test 那么提取的就是所有模块被不同的 chunk 引入超过 1 次的
                twice: {
                    // test: /[\\/]node_modules[\\/]/,
                    chunks: 'all',
                    name: 'twice',
                    priority: 6,
                    minChunks: 2
                },
                // default 和 vendors 是默认缓存组，可通过 optimization.splitChunks.cacheGroups.default: false 来禁用
                default: {
                    minChunks: 2,
                    priority: -20,
                    reuseExistingChunk: true
                },
                defaultVendors: {
                    test: /[\\/]node_modules[\\/]/,
                    priority: -10
                },
                styles: {
                    name: 'app',
                    test: (module: any) =>{
                      return module.nameForCondition && /\.vue$/.test(module.nameForCondition()) && !/^javascript/.test(module.type)
                    },
                    chunks: 'async',
                    minChunks: 1,
                    enforce: true
                }
            }
        }
    },
    watchOptions: {
        aggregateTimeout: 600,
        poll: 1000,
        ignored: ['node_modules/**'],

    },
    stats: {
        hash: true,
        publicPath: true,
        assets: false,
        assetsSort: '!size',
        builtAt: true,
        colors: true,
        depth: true,
        modules: true,
        logging: 'error'
    },
    module: {
        rules: [
            {
              oneOf: [
                {
                  test: /\.(css|postcss)$/,
                  use: [
                      // 'cache-loader',
                      'style-loader',
                      {
                          loader: 'css-loader',
                        //   options: {
                        //       importLoaders: 2
                        //   }
                      },
                      {
                          loader: 'postcss-loader',
                          options: {
                            // importLoaders: 2,
                              postcssOptions: {
                                  config: path.resolve(__dirname, '..', 'postcss.config.js')
                              }
                          }
                      }
                  ]
                },
                {
                  test: /\.s[ac]ss$/i,
                  use: [
                      // 'cache-loader',
                      'style-loader',
                      // Translates CSS into CommonJS
                      {
                          loader: 'css-loader',
                          options: {
                            //   importLoaders: 1
                          }
                      },
                      // Compiles Sass to CSS
                      'sass-loader'
                  ]
                }
              ]
            }
        ]
    },
    cache: { type: 'filesystem' },
    plugins: [
        new webpack.DefinePlugin(config.dev.env),

        new webpack.DllReferencePlugin({
            context: __dirname,
            manifest: manifest
        }),

        new webpack.HotModuleReplacementPlugin(),

        new webpack.NoEmitOnErrorsPlugin(),

        new HtmlWebpackPlugin({
            filename: 'index.html',
            template: 'index-dev.html',
            inject: true
        }),

        new HtmlWebpackPlugin({
            filename: 'login_success.html',
            template: 'login_success.html',
            inject: true
        }),

        // new AnalyzerPlugin.BundleAnalyzerPlugin()
        // new FriendlyErrorsPlugin()
    ]
})

// Object.keys(webpackConfig.entry).forEach(name => {
//     webpackConfig.entry[name] = ['./build/dev-client'].concat(webpackConfig.entry[name])
// })

export default webpackConfig
