const path = require('path');
const webpack = require('webpack');
const WebpackShellPlugin = require('webpack-shell-plugin');
const Dotenv = require('dotenv-webpack');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const NyanProgressPlugin = require('nyan-progress-webpack-plugin');

const plugins = [
    new Dotenv({
        path: '../.env',
        safe: false, // load '.env.example' to verify the '.env' variables are all set. Can also be a string to a different file.
        systemvars: true, // load all the predefined 'process.env' variables which will override local dotenv specs.
        silent: false, // hide any errors
    }),
    // copy index.html to dist
    // new CopyWebpackPlugin([{
    //     from: './index.html'
    // }]),
    new HtmlWebpackPlugin({
        title: 'Laxy',
        filename: 'index.html',
        template: 'index.html',
        // favicon: 'assets/favicon.ico',
        hash: true,
  })
];

/*
plugins.push(new WebpackShellPlugin({
  // onBuildStart: ['echo "Starting"'],
  onBuildEnd: ['python3 ../manage.py collectstatic --no-input'],
  dev: false, // so that it always runs after rebuild in --watch mode
}));
*/

module.exports = {
    watch: false,
    entry: "./src/index.ts",
    output: {
        path: path.resolve(__dirname, './dist'),
        filename: process.env.NODE_ENV === 'production' ? "bundle.[hash].js": "bundle.js",
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader',
                options: {
                    loaders: {
                        // Since sass-loader (weirdly) has SCSS as its default parse mode, we map
                        // the "scss" and "sass" values for the lang attribute to the right configs here.
                        // other preprocessors should work out of the box, no loader config like this necessary.
                        'scss': 'vue-style-loader!css-loader!sass-loader',
                        'sass': 'vue-style-loader!css-loader!sass-loader?indentedSyntax',
                    }
                    // other vue-loader options go here
                }
            },
            {
                test: /\.tsx?$/,
                loader: 'ts-loader',
                exclude: /node_modules/,
                options: {
                    appendTsSuffixTo: [/\.vue$/],
                }
            },
            {
                test: /\.(png|jpg|gif|svg)$/,
                loader: 'file-loader',
                options: {
                    name: '[name].[ext]?[hash]',
                    outputPath: 'assets/',
                }
            },
            {
                test: /\.css$/,
                // loader: 'style-loader!css-loader',
                use: ['style-loader', 'css-loader']
            },
        ]
    },
    resolve: {
        extensions: ['.ts', '.js', '.vue', '.json'],
        alias: {
            'vue$': 'vue/dist/vue.esm.js',
        }
    },
    plugins: plugins,
    devServer: {
        historyApiFallback: true,
        noInfo: true
    },
    performance: {
        hints: false
    },
    devtool: 'inline-source-map',
};

if (process.env.NYAN === 'true') {
    module.exports.plugins = (module.exports.plugins || []).concat([
        new NyanProgressPlugin()
    ]);
}

module.exports.plugins = (module.exports.plugins || []).concat([
    new webpack.DefinePlugin({
        'process.env': {
            // NODE_ENV is used in some dependencies and breaks things if replaced via webpack DefinePlugin pre-processing.
            // NODE_ENV: JSON.stringify(process.env.NODE_ENV) || JSON.stringify('production'),
            LAXY_ENV: JSON.stringify(process.env.LAXY_ENV) || JSON.stringify(process.env.NODE_ENV) || JSON.stringify('prod'),
            LAXY_FRONTEND_API_URL: JSON.stringify(process.env.LAXY_FRONTEND_API_URL) || JSON.stringify('http://localhost:8001'),
            LAXY_FRONTEND_URL: JSON.stringify(process.env.LAXY_FRONTEND_URL) || JSON.stringify('http://localhost:8002'),
            LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID: JSON.stringify(process.env.LAXY_FRONTEND_GOOGLE_OAUTH_CLIENT_ID) || JSON.stringify(''),
            LAXY_VERSION: JSON.stringify(process.env.GIT_COMMIT) || JSON.stringify('unspecified'),
        }
    }),
]);

if (process.env.NODE_ENV === 'production') {
    module.exports.devtool = 'source-map';
    // http://vue-loader.vuejs.org/en/workflow/production.html
    module.exports.plugins = (module.exports.plugins || []).concat([
        new webpack.optimize.UglifyJsPlugin({
            sourceMap: true,
            compress: {
                warnings: false
            }
        }),
        new webpack.LoaderOptionsPlugin({
            minimize: true
        })
    ]);
}
