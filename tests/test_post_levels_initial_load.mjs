import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync('static/js/post_levels.js', 'utf8');
const context = vm.createContext({
    console,
    document: { getElementById: () => null },
});
vm.runInContext(`${source}\nthis.PostLevelsManager = PostLevelsManager;`, context);
const { PostLevelsManager } = context;


test('initialization previews aggregates without persisting them', async () => {
    const calls = [];
    const manager = Object.create(PostLevelsManager.prototype);
    manager.bindEvents = () => calls.push('bind');
    manager.loadDaRate = async () => calls.push('da');
    manager.loadPayMatrixStages = async () => calls.push('matrix');
    manager.loadLevels = async persist => calls.push(['levels', persist]);
    manager.loadLimitInfo = async () => calls.push('limit');

    await manager.init();

    assert.deepEqual(calls, [
        'bind',
        'da',
        'matrix',
        ['levels', false],
        'limit',
    ]);
});


test('preview and persistence paths use distinct aggregate contracts', async () => {
    const requests = [];
    const fields = [];
    const aggregate = {
        special_pay: 1,
        basic_pay: 2,
        grade_pay: 3,
        local_supplementary_allowance: 4,
        vehicle_allowance: 5,
        washing_allowance: 6,
        cash_allowance: 7,
        footwear_allowance_other: 8,
        dearness_allowance: 9,
        hra_total: 10,
    };
    const manager = Object.create(PostLevelsManager.prototype);
    Object.assign(manager, {
        apiBasePath: '/api/post-levels',
        budgetPostId: 41,
        setField: (name, value) => fields.push([name, value]),
    });

    context.fetch = async (url, options) => {
        requests.push([url, options]);
        return {
            ok: true,
            json: async () => url.endsWith('/aggregates')
                ? aggregate
                : { aggregates: aggregate },
        };
    };

    await manager.syncMainForm(false);
    await manager.syncMainForm(true);

    assert.deepEqual(
        requests.map(([url, options]) => [url, options.method ?? 'GET']),
        [
            ['/api/post-levels/41/aggregates', 'GET'],
            ['/api/post-levels/41/apply-aggregates', 'POST'],
        ],
    );
    assert.equal(fields.length, 20);
    assert.deepEqual(fields.slice(0, 10), fields.slice(10));
});
