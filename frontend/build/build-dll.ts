import path from 'path'
import webpack from 'webpack'
import TerserPlugin from 'terser-webpack-plugin'
import chalk from 'chalk'
import glob from 'glob'
import ora from 'ora'

import config from './config'

const ret = glob.sync('../static/lib**', { mark: true, cwd: __dirname })

const mode = process.env.NODE_ENV === 'production' ? 'production' : 'development'
const configMap = {
    production: config.build,
    development: config.dev
}

if (!ret.length) {
    // 需要打包到一起的 js 文件
    const vendors = [
        'vue/dist/vue.esm.js',
        'vuex',
        'vue-router',
        'axios'
    ]

    const dllConf: webpack.Configuration = {
        mode,
        // 也可设置多个入口，多个 vendor，就可以生成多个 bundle
        entry: {
            lib: vendors
        },
        target: 'web',
        stats: 'verbose',
        // 输出文件的名称和路径
        output: {
            filename: '[name].bundle.js',
            path: path.join(__dirname, '..', 'static'),
            // lib.bundle.js 中暴露出的全局变量名
            library: '[name]_[fullhash]'
        },
        plugins: [
            new webpack.DefinePlugin(configMap[mode].env),
            new webpack.DllPlugin({
                path: path.join(__dirname, '..', 'static', '[name]-manifest.json'),
                name: '[name]_[fullhash]',
                context: __dirname
            }),

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

            new webpack.LoaderOptionsPlugin({
                minimize: true
            })
        ]
    }

    const spinner = ora('building dll...')
    spinner.start()

    webpack(dllConf, (err, stats) => {
        spinner.stop()
        if (err) {
            throw err
        }
        process.stdout.write(`${stats?.toString({
          colors: true,
          modules: false,
          children: false,
          chunks: false,
          chunkModules: false
        })}\n\n`)

        if (stats?.hasErrors()) {
            console.log(chalk.red('  Build failed with errors.\n'))
            process.exit(1)
        }

        console.log(chalk.cyan('  DLL Build complete.\n'))
    })
}
