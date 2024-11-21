# 排程
* 使用的排程工具是：crontab
    * 參考文章：https://blog.gtwang.org/linux/linux-crontab-cron-job-tutorial-and-examples/
    * crontab設定欄位
        ```
        # ┌───────────── 分鐘   (0 - 59)
        # │ ┌─────────── 小時   (0 - 23)
        # │ │ ┌───────── 日     (1 - 31)
        # │ │ │ ┌─────── 月     (1 - 12)
        # │ │ │ │ ┌───── 星期幾 (0 - 7，0 是週日，6 是週六，7 也是週日)
        # │ │ │ │ │
        # * * * * * /path/to/command
        ```
    * 基本的crontab範例
        ```
        # 每天早上 8 點 30 分執行
        30 08 * * * /path/to/command

        # 每週日下午 6 點 30 分執行
        30 18 * * 0 /path/to/command

        # 每週日下午 6 點 30 分執行
        30 18 * * Sun /path/to/command

        # 每年 6 月 10 日早上 8 點 30 分執行
        30 08 10 06 * /path/to/command

        # 每月 1 日、15 日、29 日晚上 9 點 30 分各執行一次
        30 21 1,15,29 * * /path/to/command

        # 每隔 10 分鐘執行一次
        */10 * * * * /path/to/command

        # 從早上 9 點到下午 6 點，凡遇到整點就執行
        00 09-18 * * * /path/to/command
        ```
* 排程檔案
    * 執行腳本在 `./server/cronjob.sh`
    * 腳本中的參數PYTHON_EXE，記得要修改！！！
    * 執行腳本時，當前目錄必須在server資料夾。
    * 指令說明
        1. list: "顯示"排程檔案。
        2. enable <service_name>: 將指定排程"新增"至排程檔案。
        3. disable <service_name>: 將指定排程從排程檔案"移除"。
    * 操作舉例
        1. `cd server`
        2. `./cronjob.sh list`
        3. `./cronjob.sh enable download_textReading_files`
        4. `./cronjob.sh enable process_tasks`
        5. `./cronjob.sh disable download_textReading_files`
        6. `./cronjob.sh disable process_tasks`
    * log
        1. <root_dir>/logfile
            * crontab在執行時，如有發生錯誤，可在此檔案看到相關紀錄，協助排除問題。
        2. <root_dir>/logs/cronjob_download_textReading_files_{date}.log
            * 指定排程：download_textReading_file.py在執行過程中產生的log。
