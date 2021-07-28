
// import retrieve from './retrieve'

const getTest = {
    message: '',
    code: 'OK',
    data: {
        total: 100,
        took: 0.29,
        list: [
            {
                index_id: 1,
                index_set_id: 1,
                bk_biz_id: 1,
                bk_biz_name: '业务名称',
                result_table_id: '结果表',
                time_field: '时间字段',
                apply_status: 'pending',
                apply_status_name: '审核状态名称',
                created_at: '2019-10-10 11:11:11',
                created_by: 'user',
                updated_at: '2019-10-10 11:11:11',
                updated_by: 'user'
            }
        ]
    },
    result: true
}
const getMyProjectList = {
    message: '',
    code: 'OK',
    data: [
        {
            project_id: 1,
            project_name: '业务名称',
            bk_biz_id: 1,
            bk_app_code: 'bk_log',
            time_zone: 'Etc/GMT-8',
            description: '项目描述'
        }
    ],
    result: true
}

export default {
    example: {
        getTest
    },
    project: {
        getMyProjectList
    }
    // retrieve
}
