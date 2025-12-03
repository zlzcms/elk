import uvicorn
# uvicorn 参数 reload_excludes  是相对于  reload_dirs 的 文件夹路径


if __name__ == '__main__':
    uvicorn.run(
        app='app:app',
        host='0.0.0.0',
        port=8000,
        reload=True
    )
