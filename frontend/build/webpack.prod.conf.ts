import { resolve, join } from 'path'
import webpack from 'webpack'
import merge from 'webpack-merge'
import MiniCssExtractPlugin from 'mini-css-extract-plugin'
import TerserPlugin from 'terser-webpack-plugin'
import CssMinimizerPlugin from 'css-minimizer-webpack-plugin'
import HtmlWebpackPlugin from 'html-webpack-plugin'
import CopyWebpackPlugin from 'copy-webpack-plugin'
import bundleAnalyzer from 'webpack-bundle-analyzer'

import config from './config'
import { assetsPath } from './util'
import baseConf from './webpack.base.conf'
import manifest from '../static/lib-manifest.json'
import ReplaceCssStaticUrl from './replace-css-static-url-plugin'

const prodConf = merge(baseConf, {
    mode: 'production',
    entry: {
        main: './src/main.ts'
    },
    output: {
        filename: assetsPath('js/[name].[chunkhash].js'),
        chunkFilename: assetsPath('js/[name].[chunkhash].js')
    },
    optimization: {
        chunkIds: 'named',
        minimizer: [
            new TerserPlugin({
                terserOptions: {
                    compress: false,
                    mangle: true,
                    output: {
                        comments: false
                    }
                },
                parallel: true
            }),
            new CssMinimizerPlugin()
        ],
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
    module: {
        rules: [
            {
                test: /\.(css|postcss)?$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    {
                        loader: 'css-loader',
                        options: {
                            importLoaders: 1
                        }
                    },
                    {
                        loader: 'postcss-loader',
                        options: {
                            postcssOptions: {
                                config: resolve(__dirname, '..', 'postcss.config.js')
                            }
                        }
                    }
                ]
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    MiniCssExtractPlugin.loader,
                    // Translates CSS into CommonJS
                    {
                        loader: 'css-loader',
                        options: {
                            importLoaders: 1
                        }
                    },
                    // Compiles Sass to CSS
                    'sass-loader'
                ]
            }
        ]
    },
    plugins: [
        new webpack.DefinePlugin(config.build.env),

        new webpack.DllReferencePlugin({
            context: __dirname,
            manifest: manifest
        }),

        new HtmlWebpackPlugin({
            filename: 'index.html',
            template: join(__dirname, '..', '/index.html'),
            inject: true,
            minify: {
                removeComments: true,
                collapseWhitespace: true,
                removeAttributeQuotes: true
            },
            sourceMap: true,
            // 如果打开 vendor 和 manifest 那么需要配置 chunksSortMode 保证引入 script 的顺序
            // chunksSortMode: 'dependency',
            chunksSortMode: 'auto',
            bundlehash: Date.now()
        }),

        new MiniCssExtractPlugin({
            filename: assetsPath('css/[name].[contenthash].css'),
            ignoreOrder: true
        }),

        new CopyWebpackPlugin({
          patterns: [{
              from: resolve(__dirname, '../static'),
              to: config.build.assetsSubDirectory,
              globOptions: {
                  ignore: ['.*']
              }
          }]
        }),

        new ReplaceCssStaticUrl()
    ]
})

if (config.build.bundleAnalyzerReport) {
    const BundleAnalyzerPlugin = bundleAnalyzer.BundleAnalyzerPlugin
    prodConf.plugins?.push(new BundleAnalyzerPlugin(
        {
            analyzerPort: 7777
        }
        // {
        //     //  可以是`server`，`static`或`disabled`。
        //     //  在`server`模式下，分析器将启动HTTP服务器来显示软件包报告。
        //     //  在“静态”模式下，会生成带有报告的单个HTML文件。
        //     //  在`disabled`模式下，你可以使用这个插件来将`generateStatsFile`设置为`true`来生成Webpack Stats JSON文件。
        //     analyzerMode: 'server',
        //     //  将在“服务器”模式下使用的主机启动HTTP服务器。
        //     analyzerHost: '127.0.0.1',
        //     //  将在“服务器”模式下使用的端口启动HTTP服务器。
        //     analyzerPort: 8888,
        //     //  路径捆绑，将在`static`模式下生成的报告文件。
        //     //  相对于捆绑输出目录。
        //     reportFilename: 'report.html',
        //     //  模块大小默认显示在报告中。
        //     //  应该是`stat`，`parsed`或者`gzip`中的一个。
        //     //  有关更多信息，请参见“定义”一节。
        //     defaultSizes: 'parsed',
        //     //  在默认浏览器中自动打开报告
        //     openAnalyzer: true,
        //     //  如果为true，则Webpack Stats JSON文件将在bundle输出目录中生成
        //     generateStatsFile: false,
        //     //  如果`generateStatsFile`为`true`，将会生成Webpack Stats JSON文件的名字。
        //     //  相对于捆绑输出目录。
        //     statsFilename: 'stats.json',
        //     //  stats.toJson（）方法的选项。
        //     //  例如，您可以使用`source：false`选项排除统计文件中模块的来源。
        //     //  在这里查看更多选项：https：  //github.com/webpack/webpack/blob/webpack-1/lib/Stats.js#L21
        //     statsOptions: null,
        //     logLevel: 'info' //日志级别。可以是'信息'，'警告'，'错误'或'沉默'。
        // }
    ))
}

export default prodConf
