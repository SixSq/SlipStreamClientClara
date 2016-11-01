import click

from slipstream.cli import types


@click.command()
@click.argument('param', type=types.NodeKeyValue())
def cmd(param):
    key, value = param
    click.echo('{}\n{}'.format(key, value))


class TestNodeKeyValue(object):

    def test_component_param(self, runner):
        result = runner.invoke(cmd, ['scale=2'])
        assert result.exit_code == 0
        assert result.output == 'parameter--scale\n2\n'

    def test_application_param(self, runner):
        result = runner.invoke(cmd, ['db:scale=2'])
        assert result.exit_code == 0
        assert result.output == 'parameter--node--db--scale\n2\n'

    def test_fail(self, runner):
        result = runner.invoke(cmd, ['db_scale'])
        assert result.exit_code == 2
        assert result.exception

    def test_complex_key(self, runner):
        result = runner.invoke(cmd, ['db:scale:min=2'])
        assert result.exit_code == 0
        assert result.output == 'parameter--node--db--scale:min\n2\n'

    def test_complex_value(self, runner):
        result = runner.invoke(cmd, ['db:scale=a=2'])
        assert result.exit_code == 0
        assert result.output == 'parameter--node--db--scale\na=2\n'




