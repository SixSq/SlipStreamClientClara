import click

from slipstream.cli import types


@click.command()
@click.argument('param', type=types.NodeKeyValue())
def cmd(param):
    node, (key, value) = param
    click.echo('%s\n%s\n%s' % (node, key, value))


class TestNodeKeyValue(object):

    def test_ok(self, runner):
        result = runner.invoke(cmd, ['db:scale=2'])
        assert result.exit_code == 0
        assert result.output == 'db\nscale\n2\n'
        
    def test_fail(self, runner):
        result = runner.invoke(cmd, ['db_scale=2'])
        assert result.exit_code == 2
        assert result.exception
        
    def test_complex_key(self, runner):
        result = runner.invoke(cmd, ['db:scale:min=2'])
        assert result.exit_code == 0
        assert result.output == 'db\nscale:min\n2\n'
        
    def test_complex_value(self, runner):
        result = runner.invoke(cmd, ['db:scale=a=2'])
        assert result.exit_code == 0
        assert result.output == 'db\nscale\na=2\n'
    



